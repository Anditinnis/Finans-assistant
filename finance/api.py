import json
import logging
import os
import secrets
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from accounts.models import LinkCode, Profile
from .models import Category, Transaction

logger = logging.getLogger(__name__)

VALID_TYPES = ('income', 'expense')
MAX_AMOUNT = Decimal('99999999.99')
MAX_AVATAR_BYTES = 5 * 1024 * 1024


# ============================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================

def get_api_secret_key():
    """Ключ читается лениво, чтобы отсутствие настройки не роняло импорт Django."""
    return getattr(settings, 'API_SECRET_KEY', '') or os.getenv('API_SECRET_KEY', '')


def check_key(request):
    expected = get_api_secret_key()
    if not expected:
        logger.error('API_SECRET_KEY не настроен — запросы к API отклонены')
        return False
    key = request.headers.get('x-api-key', '')
    return secrets.compare_digest(key, expected)


def api_error(message, status=400):
    return JsonResponse({'error': message}, status=status)


def parse_json_body(request):
    """Безопасно разбирает JSON-тело запроса."""
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError('Некорректный JSON в теле запроса')
    if not isinstance(data, dict):
        raise ValueError('Ожидается JSON-объект')
    return data


def parse_vk_id(value):
    if value is None or value == '':
        raise ValueError('vk_id обязателен')
    try:
        vk_id = int(value)
    except (TypeError, ValueError):
        raise ValueError('vk_id должен быть числом')
    if vk_id <= 0:
        raise ValueError('vk_id должен быть положительным')
    return vk_id


def parse_amount(value):
    if value is None or value == '' or isinstance(value, bool):
        raise ValueError('Сумма обязательна и должна быть числом')
    try:
        amount = Decimal(str(value).replace(',', '.'))
    except (InvalidOperation, ValueError):
        raise ValueError('Сумма должна быть числом')
    if not amount.is_finite() or amount <= 0:
        raise ValueError('Сумма должна быть больше нуля')
    if amount > MAX_AMOUNT:
        raise ValueError('Сумма слишком большая')
    return amount.quantize(Decimal('0.01'))


def parse_type(value, default='expense'):
    transaction_type = value or default
    if transaction_type not in VALID_TYPES:
        raise ValueError('Тип операции должен быть income или expense')
    return transaction_type


def parse_category_name(value, default='Прочее'):
    name = value or default
    if not isinstance(name, str):
        raise ValueError('Название категории должно быть строкой')
    name = name.strip()
    if not name:
        raise ValueError('Название категории не может быть пустым')
    if len(name) > 50:
        raise ValueError('Название категории слишком длинное (максимум 50 символов)')
    return name


def parse_date(value):
    if not value:
        return timezone.localdate()
    if not isinstance(value, str):
        raise ValueError('Дата должна быть строкой в формате YYYY-MM-DD')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError('Дата должна быть в формате YYYY-MM-DD')


def download_vk_avatar(profile, avatar_url):
    """Скачивает аватар из VK и сохраняет в профиль."""
    if not avatar_url or not isinstance(avatar_url, str):
        return
    try:
        resp = requests.get(avatar_url, timeout=10)
        resp.raise_for_status()
        if len(resp.content) > MAX_AVATAR_BYTES:
            logger.warning('Аватар VK больше 5 МБ, пропускаем загрузку')
            return
        file_name = f"vk_{profile.vk_id}.jpg"
        profile.avatar.save(file_name, ContentFile(resp.content), save=False)
        profile.save()
        logger.info('Аватар из VK сохранён: %s', file_name)
    except Exception:
        logger.exception('Не удалось загрузить аватар из VK')


# ============================================================
# ТРАНЗАКЦИИ
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_add_transaction(request):
    if not check_key(request):
        return api_error("Invalid API key", 401)

    try:
        data = parse_json_body(request)
        vk_id = parse_vk_id(data.get("vk_id"))
        amount = parse_amount(data.get("amount"))
        category_name = parse_category_name(data.get("category"))
        t_type = parse_type(data.get("type"))
        transaction_date = parse_date(data.get("date"))
        comment = data.get("comment") or "Добавлено из ВК-бота"
        if not isinstance(comment, str):
            raise ValueError('Комментарий должен быть строкой')
        comment = comment.strip()[:200] or "Добавлено из ВК-бота"
    except ValueError as e:
        return api_error(str(e), 400)

    profile = Profile.objects.filter(vk_id=vk_id).first()
    if not profile:
        return api_error("VK не привязан", 404)

    try:
        category, _ = Category.objects.get_or_create(
            user=profile.user, name=category_name, type=t_type,
            defaults={'color': '#6366f1', 'icon': '💰'}
        )
        transaction = Transaction.objects.create(
            user=profile.user, category=category, amount=amount,
            date=transaction_date, comment=comment, source='vk'
        )
    except IntegrityError:
        logger.exception('Не удалось создать транзакцию для vk_id=%s', vk_id)
        return api_error("Не удалось сохранить операцию", 400)
    except Exception:
        logger.exception('Ошибка при добавлении транзакции для vk_id=%s', vk_id)
        return api_error("Внутренняя ошибка сервера", 500)

    return JsonResponse({"status": "ok", "transaction_id": transaction.id})


@csrf_exempt
@require_http_methods(["POST"])
def api_get_balance(request):
    if not check_key(request):
        return api_error("Invalid API key", 401)

    try:
        data = parse_json_body(request)
        vk_id = parse_vk_id(data.get("vk_id"))
    except ValueError as e:
        return api_error(str(e), 400)

    profile = Profile.objects.filter(vk_id=vk_id).first()
    if not profile:
        return api_error("VK не привязан", 404)

    try:
        totals = Transaction.objects.filter(user=profile.user).aggregate(
            income=Sum('amount', filter=Q(category__type='income')),
            expense=Sum('amount', filter=Q(category__type='expense'))
        )
    except Exception:
        logger.exception('Ошибка при подсчёте баланса для vk_id=%s', vk_id)
        return api_error("Внутренняя ошибка сервера", 500)

    income = float(totals['income'] or 0)
    expense = float(totals['expense'] or 0)
    return JsonResponse({"balance": income - expense, "income": income, "expenses": expense})


@csrf_exempt
@require_http_methods(["GET"])
def api_get_transactions(request):
    if not check_key(request):
        return api_error("Invalid API key", 401)

    try:
        vk_id = parse_vk_id(request.GET.get("vk_id"))
    except ValueError as e:
        return api_error(str(e), 400)

    profile = Profile.objects.filter(vk_id=vk_id).first()
    if not profile:
        return api_error("VK не привязан", 404)

    try:
        qs = Transaction.objects.filter(user=profile.user).select_related('category')
        items = [{
            "id": t.id, "type": t.category.type, "amount": float(t.amount),
            "category": t.category.name, "date": t.date.isoformat(), "comment": t.comment,
        } for t in qs]
    except Exception:
        logger.exception('Ошибка при получении транзакций для vk_id=%s', vk_id)
        return api_error("Внутренняя ошибка сервера", 500)

    return JsonResponse({"transactions": items})


@csrf_exempt
@require_http_methods(["GET"])
def api_get_user_by_vk(request, vk_id):
    if not check_key(request):
        return api_error("Invalid API key", 401)
    profile = Profile.objects.filter(vk_id=vk_id).first()
    if not profile:
        return api_error("VK не привязан", 404)
    return JsonResponse({"user_id": profile.user_id})


# ============================================================
# ПРИВЯЗКА VK
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_link_vk(request):
    if not check_key(request):
        return api_error("Invalid API key", 401)

    try:
        data = parse_json_body(request)
        vk_id = parse_vk_id(data.get("vk_id"))
        code = data.get("code")
        avatar_url = data.get("avatar_url")
        if not isinstance(code, str) or not code.strip():
            raise ValueError('Код обязателен')
        code = code.strip()
    except ValueError as e:
        return api_error(str(e), 400)

    link = LinkCode.objects.filter(code=code).first()
    if not link:
        return api_error("Код недействителен или истёк", 400)
    if link.is_expired():
        link.delete()
        return api_error("Код недействителен или истёк", 400)

    if Profile.objects.filter(vk_id=vk_id).exists():
        return api_error("Этот VK уже привязан к другому аккаунту", 409)

    profile, _ = Profile.objects.get_or_create(user=link.user)
    profile.vk_id = vk_id
    try:
        profile.save()
    except IntegrityError:
        return api_error("Этот VK уже привязан", 409)

    download_vk_avatar(profile, avatar_url)

    link.delete()
    return JsonResponse({"status": "ok", "message": "Привязано"})

import json
import os
import secrets
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Sum, Q
from django.db import IntegrityError
from django.core.files.base import ContentFile
from .models import Transaction, Category
from accounts.models import Profile, LinkCode


API_SECRET_KEY = os.getenv("API_SECRET_KEY")
if not API_SECRET_KEY:
    raise RuntimeError("API_SECRET_KEY не найден в .env")


def check_key(request):
    key = request.headers.get("x-api-key", "")
    return secrets.compare_digest(key, API_SECRET_KEY)


def download_vk_avatar(profile, avatar_url):
    """Скачивает аватар из VK и сохраняет в профиль."""
    if not avatar_url:
        return
    try:
        resp = requests.get(avatar_url, timeout=10)
        resp.raise_for_status()
        file_name = f"vk_{profile.vk_id}.jpg"
        profile.avatar.save(file_name, ContentFile(resp.content), save=False)
        profile.save()
        print(f"Аватар из VK сохранён: {file_name}")
    except Exception as e:
        print(f"Не удалось загрузить аватар из VK: {e}")


@csrf_exempt
@require_http_methods(["POST"])
def api_add_transaction(request):
    if not check_key(request):
        return JsonResponse({"error": "Invalid API key"}, status=401)
    try:
        data = json.loads(request.body)
        vk_id = data.get("vk_id")
        amount = data.get("amount")
        category_name = data.get("category", "Прочее")
        t_type = data.get("type", "expense")
        profile = Profile.objects.filter(vk_id=vk_id).first()
        if not profile:
            return JsonResponse({"error": "VK не привязан"}, status=404)
        category, _ = Category.objects.get_or_create(
            user=profile.user, name=category_name, type=t_type,
            defaults={'color': '#6366f1', 'icon': '💰'}
        )
        t = Transaction.objects.create(
            user=profile.user, category=category, amount=amount,
            date=timezone.now().date(), comment="Добавлено из ВК-бота", source='vk'
        )
        return JsonResponse({"status": "ok", "transaction_id": t.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_get_balance(request):
    if not check_key(request):
        return JsonResponse({"error": "Invalid API key"}, status=401)
    try:
        data = json.loads(request.body)
        vk_id = data.get("vk_id")
        profile = Profile.objects.filter(vk_id=vk_id).first()
        if not profile:
            return JsonResponse({"error": "VK не привязан"}, status=404)
        totals = Transaction.objects.filter(user=profile.user).aggregate(
            income=Sum('amount', filter=Q(category__type='income')),
            expense=Sum('amount', filter=Q(category__type='expense'))
        )
        income = float(totals['income'] or 0)
        expense = float(totals['expense'] or 0)
        return JsonResponse({"balance": income - expense, "income": income, "expenses": expense})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_transactions(request):
    if not check_key(request):
        return JsonResponse({"error": "Invalid API key"}, status=401)
    try:
        vk_id = request.GET.get("vk_id")
        if not vk_id:
            return JsonResponse({"error": "vk_id обязателен"}, status=400)
        profile = Profile.objects.filter(vk_id=vk_id).first()
        if not profile:
            return JsonResponse({"error": "VK не привязан"}, status=404)
        qs = Transaction.objects.filter(user=profile.user).select_related('category')
        items = [{
            "id": t.id, "type": t.category.type, "amount": float(t.amount),
            "category": t.category.name, "date": t.date.isoformat(), "comment": t.comment,
        } for t in qs]
        return JsonResponse({"transactions": items})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_user_by_vk(request, vk_id):
    if not check_key(request):
        return JsonResponse({"error": "Invalid API key"}, status=401)
    profile = Profile.objects.filter(vk_id=vk_id).first()
    if not profile:
        return JsonResponse({"error": "VK не привязан"}, status=404)
    return JsonResponse({"user_id": profile.user_id})


@csrf_exempt
@require_http_methods(["POST"])
def api_link_vk(request):
    if not check_key(request):
        return JsonResponse({"error": "Invalid API key"}, status=401)
    try:
        data = json.loads(request.body)
        vk_id = data.get("vk_id")
        code = data.get("code")
        avatar_url = data.get("avatar_url")

        link = LinkCode.objects.filter(code=code).first()
        if not link or link.is_expired():
            return JsonResponse({"error": "Код недействителен или истёк"}, status=400)

        if Profile.objects.filter(vk_id=vk_id).exists():
            return JsonResponse({"error": "Этот VK уже привязан к другому аккаунту"}, status=409)

        profile, _ = Profile.objects.get_or_create(user=link.user)
        profile.vk_id = vk_id
        try:
            profile.save()
        except IntegrityError:
            return JsonResponse({"error": "Этот VK уже привязан"}, status=409)

        if avatar_url:
            download_vk_avatar(profile, avatar_url)

        link.delete()
        return JsonResponse({"status": "ok", "message": "Привязано"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
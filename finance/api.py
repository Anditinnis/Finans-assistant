import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Sum, Q
from .models import Transaction, Category
from accounts.models import Profile, LinkCode


API_SECRET_KEY = "super-secret-key-change-me"


def check_key(request):
    return request.headers.get("x-api-key") == API_SECRET_KEY


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
            user=profile.user,
            name=category_name,
            type=t_type,
            defaults={'color': '#6366f1', 'icon': '💰'}
        )

        t = Transaction.objects.create(
            user=profile.user,
            category=category,
            amount=amount,
            date=timezone.now().date(),
            comment="Добавлено из ВК-бота",
            source='vk'
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

        return JsonResponse({
            "balance": income - expense,
            "income": income,
            "expenses": expense
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_link_vk(request):
    if not check_key(request):
        return JsonResponse({"error": "Invalid API key"}, status=401)

    try:
        data = json.loads(request.body)
        vk_id = data.get("vk_id")
        code = data.get("code")

        link = LinkCode.objects.filter(code=code).first()
        if not link or link.is_expired():
            return JsonResponse({"error": "Код недействителен или истёк"}, status=400)

        profile, _ = Profile.objects.get_or_create(user=link.user)
        profile.vk_id = vk_id
        profile.save()
        link.delete()

        return JsonResponse({"status": "ok", "message": "Привязано"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
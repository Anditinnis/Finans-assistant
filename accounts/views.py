import os
import time
from decimal import Decimal

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db.models import Sum, Q
from django.utils import timezone

from .forms import RegisterForm, ProfileForm
from .models import Profile, LinkCode
from finance.models import Transaction


def get_bot_status():
    file_path = os.path.join(settings.BASE_DIR, 'bot_heartbeat.txt')
    if not os.path.exists(file_path):
        return "Бот не запускался"
    try:
        last_time = os.path.getmtime(file_path)
        if time.time() - last_time < 120:
            return "Бот работает"
        return "Бот не отвечает (нет активности)"
    except Exception:
        return "Ошибка проверки статуса"


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


@login_required
def dashboard(request):
    qs = Transaction.objects.filter(user=request.user).select_related('category')
    today = timezone.localdate()
    month_qs = qs.filter(date__year=today.year, date__month=today.month)
    month_totals = month_qs.aggregate(
        income=Sum('amount', filter=Q(category__type='income')),
        expense=Sum('amount', filter=Q(category__type='expense')),
    )
    all_totals = qs.aggregate(
        income=Sum('amount', filter=Q(category__type='income')),
        expense=Sum('amount', filter=Q(category__type='expense')),
    )
    month_income = month_totals['income'] or Decimal('0')
    month_expense = month_totals['expense'] or Decimal('0')
    balance = (all_totals['income'] or Decimal('0')) - (all_totals['expense'] or Decimal('0'))
    bot_status = get_bot_status()
    return render(request, 'dashboard.html', {
        'balance': balance,
        'month_income': month_income,
        'month_expense': month_expense,
        'transactions_count': qs.count(),
        'last_transactions': qs[:5],
        'bot_status': bot_status,
    })


@login_required
def link_vk_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    code = None
    error = None
    if request.method == 'POST':
        if profile.vk_id:
            error = 'VK уже привязан'
        else:
            link = LinkCode.generate_for(request.user)
            code = link.code
    return render(request, 'link_vk.html', {
        'code': code,
        'error': error,
        'profile': profile,
    })


@login_required
def unlink_vk(request):
    if request.method == 'POST':
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if profile.vk_id:
            profile.vk_id = None
            profile.save()
        return redirect('profile')
    return redirect('profile')


@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'accounts/profile_edit.html', {'form': form})
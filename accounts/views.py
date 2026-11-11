import requests
from decimal import Decimal

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Sum, Q
from django.utils import timezone

from .forms import RegisterForm
from .models import Profile, LinkCode
from finance.models import Transaction


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            Profile.objects.create(user=user)
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

    return render(request, 'dashboard.html', {
        'balance': balance,
        'month_income': month_income,
        'month_expense': month_expense,
        'transactions_count': qs.count(),
        'last_transactions': qs[:5],
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
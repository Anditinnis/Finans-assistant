from datetime import date
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone

from .models import Category, Transaction
from .forms import TransactionForm, CategoryForm


@login_required
def transactions_list(request):
    """Список транзакций с фильтрами и формой быстрого добавления."""
    qs = Transaction.objects.filter(user=request.user).select_related('category')

    # Фильтры
    type_filter = request.GET.get('type')  # income / expense
    cat_filter = request.GET.get('category')
    period = request.GET.get('period')  # month / all

    if type_filter in ('income', 'expense'):
        qs = qs.filter(category__type=type_filter)
    if cat_filter:
        qs = qs.filter(category_id=cat_filter)
    if period == 'month':
        today = timezone.localdate()
        qs = qs.filter(date__year=today.year, date__month=today.month)

    # Форма добавления
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            t = form.save(commit=False)
            t.user = request.user
            t.source = 'web'
            t.save()
            messages.success(request, f'Транзакция добавлена: {t}')
            return redirect('transactions_list')
        else:
            messages.error(request, 'Проверь форму — есть ошибки')
    else:
        form = TransactionForm(user=request.user, initial={'date': date.today()})

    # Итоги по текущей выборке
    totals = qs.aggregate(
        income=Sum('amount', filter=Q(category__type='income')),
        expense=Sum('amount', filter=Q(category__type='expense')),
    )
    income = totals['income'] or Decimal('0')
    expense = totals['expense'] or Decimal('0')

    categories = Category.objects.filter(user=request.user)

    return render(request, 'finance/transactions_list.html', {
        'transactions': qs,
        'form': form,
        'categories': categories,
        'type_filter': type_filter or '',
        'cat_filter': cat_filter or '',
        'period': period or 'all',
        'income_total': income,
        'expense_total': expense,
        'balance': income - expense,
    })


@login_required
def transaction_delete(request, pk):
    t = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        t.delete()
        messages.success(request, 'Транзакция удалена')
    return redirect('transactions_list')


@login_required
def transaction_edit(request, pk):
    t = get_object_or_404(Transaction, pk=pk, user=request.user)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=t, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Транзакция обновлена')
            return redirect('transactions_list')
    else:
        form = TransactionForm(instance=t, user=request.user)

    return render(request, 'finance/transaction_edit.html', {
        'form': form,
        'transaction': t,
    })


@login_required
def categories_list(request):
    qs = Category.objects.filter(user=request.user)

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.user = request.user
            try:
                c.save()
                messages.success(request, f'Категория «{c.name}» создана')
            except Exception:
                messages.error(request, 'Категория с таким названием и типом уже есть')
            return redirect('categories_list')
    else:
        form = CategoryForm()

    return render(request, 'finance/categories_list.html', {
        'categories': qs,
        'form': form,
    })


@login_required
def category_delete(request, pk):
    c = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        c.delete()
        messages.success(request, 'Категория удалена (вместе с её транзакциями)')
    return redirect('categories_list')
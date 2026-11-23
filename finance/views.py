from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.db.models.functions import ExtractWeekDay, TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import CategoryForm, TransactionForm
from .models import Category, Transaction


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
            # сохраняем текущие фильтры, чтобы пользователь не терял выборку
            params = request.GET.copy()
            params['added'] = '1'
            return redirect(f"{reverse('transactions_list')}?{params.urlencode()}")
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
            except IntegrityError:
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
        if c.transactions.exists():
            messages.error(
                request,
                'Нельзя удалить категорию, в которой есть транзакции. '
                'Сначала удали или перенеси их в другую категорию.'
            )
        else:
            c.delete()
            messages.success(request, 'Категория удалена')
    return redirect('categories_list')


MONTHS_RU = [
    'янв', 'фев', 'мар', 'апр', 'май', 'июн',
    'июл', 'авг', 'сен', 'окт', 'ноя', 'дек',
]

PERIODS = {
    'month': 'Текущий месяц',
    'quarter': 'Квартал',
    'year': 'Год',
    'all': 'Всё время',
}


def _period_start(period, today):
    """Возвращает начало периода или None для «всё время»."""
    if period == 'month':
        return today.replace(day=1)
    if period == 'quarter':
        first_month = ((today.month - 1) // 3) * 3 + 1
        return today.replace(month=first_month, day=1)
    if period == 'year':
        return today.replace(month=1, day=1)
    return None


@login_required
def analytics(request):
    """Аналитика на реальных данных пользователя."""
    period = request.GET.get('period', 'month')
    if period not in PERIODS:
        period = 'month'

    today = timezone.localdate()
    start = _period_start(period, today)

    qs = Transaction.objects.filter(user=request.user).select_related('category')
    if start:
        qs = qs.filter(date__gte=start, date__lte=today)

    totals = qs.aggregate(
        income=Sum('amount', filter=Q(category__type='income')),
        expense=Sum('amount', filter=Q(category__type='expense')),
    )
    income = totals['income'] or Decimal('0')
    expense = totals['expense'] or Decimal('0')

    # Расходы по категориям
    by_category = list(
        qs.filter(category__type='expense')
        .values('category__name', 'category__color', 'category__icon')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    # Динамика доходов и расходов за последние 6 месяцев
    months = []
    for offset in range(5, -1, -1):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        months.append((year, month))

    first_month_date = date(months[0][0], months[0][1], 1)
    monthly_rows = (
        Transaction.objects.filter(user=request.user, date__gte=first_month_date)
        .annotate(month=TruncMonth('date'))
        .values('month', 'category__type')
        .annotate(total=Sum('amount'))
    )
    monthly_map = {}
    for row in monthly_rows:
        key = (row['month'].year, row['month'].month, row['category__type'])
        monthly_map[key] = float(row['total'] or 0)

    monthly_labels = []
    monthly_income = []
    monthly_expense = []
    for year, month in months:
        monthly_labels.append(f'{MONTHS_RU[month - 1]} {year}')
        monthly_income.append(monthly_map.get((year, month, 'income'), 0))
        monthly_expense.append(monthly_map.get((year, month, 'expense'), 0))

    # Расходы по дням недели (Пн..Вс)
    weekday_rows = (
        qs.filter(category__type='expense')
        .annotate(weekday=ExtractWeekDay('date'))
        .values('weekday')
        .annotate(total=Sum('amount'))
    )
    weekday_values = [0.0] * 7
    for row in weekday_rows:
        # SQLite: 1 = воскресенье ... 7 = суббота
        index = (int(row['weekday']) + 5) % 7
        weekday_values[index] = float(row['total'] or 0)

    # Средний расход в день
    if start:
        days = max((today - start).days + 1, 1)
    else:
        first_date = qs.order_by('date').values_list('date', flat=True).first()
        days = max((today - first_date).days + 1, 1) if first_date else 1

    top_category = by_category[0]['category__name'] if by_category else None

    chart_data = {
        'category': {
            'labels': [
                f"{row['category__icon'] or '💰'} {row['category__name']}"
                for row in by_category
            ],
            'values': [float(row['total'] or 0) for row in by_category],
            'colors': [row['category__color'] or '#6366f1' for row in by_category],
        },
        'monthly': {
            'labels': monthly_labels,
            'income': monthly_income,
            'expense': monthly_expense,
        },
        'weekday': {
            'labels': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
            'values': weekday_values,
        },
    }

    return render(request, 'finance/analytics.html', {
        'period': period,
        'periods': PERIODS,
        'income_total': income,
        'expense_total': expense,
        'balance': income - expense,
        'average_per_day': (expense / Decimal(days)).quantize(Decimal('0.01')),
        'top_category': top_category,
        'transactions_count': qs.count(),
        'chart_data': chart_data,
        'has_data': bool(by_category or income or expense),
    })
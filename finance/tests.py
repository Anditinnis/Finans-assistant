import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import LinkCode, Profile

from .forms import TransactionForm
from .models import Category, Transaction

API_KEY = 'test-secret-key'


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.expense = Category.objects.create(user=self.user, name='Еда', type='expense')
        self.income = Category.objects.create(user=self.user, name='Зарплата', type='income')

    def test_transaction_str_and_is_income(self):
        income = Transaction.objects.create(
            user=self.user, category=self.income,
            amount=Decimal('1000.00'), date=timezone.localdate()
        )
        self.assertTrue(income.is_income)
        self.assertIn('+1000.00', str(income))

        expense = Transaction.objects.create(
            user=self.user, category=self.expense,
            amount=Decimal('500.00'), date=timezone.localdate()
        )
        self.assertFalse(expense.is_income)
        self.assertIn('-500.00', str(expense))

    def test_category_is_unique_per_user_and_type(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(user=self.user, name='Еда', type='expense')

    def test_same_name_allowed_for_different_type(self):
        category = Category.objects.create(user=self.user, name='Еда', type='income')
        self.assertEqual(category.type, 'income')


class TransactionFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.other = User.objects.create_user('bob', password='pass12345')
        self.category = Category.objects.create(user=self.user, name='Еда', type='expense')
        self.foreign = Category.objects.create(user=self.other, name='Еда', type='expense')

    def _form(self, **overrides):
        data = {
            'category': self.category.pk,
            'amount': '100',
            'date': timezone.localdate().isoformat(),
            'comment': '',
        }
        data.update(overrides)
        return TransactionForm(data=data, user=self.user)

    def test_accepts_valid_data(self):
        self.assertTrue(self._form().is_valid())

    def test_rejects_non_positive_amount(self):
        for value in ('0', '-10'):
            form = self._form(amount=value)
            self.assertFalse(form.is_valid(), value)
            self.assertIn('amount', form.errors)

    def test_rejects_foreign_category(self):
        form = self._form(category=self.foreign.pk)
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)


class TransactionViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.other = User.objects.create_user('bob', password='pass12345')
        self.category = Category.objects.create(user=self.user, name='Еда', type='expense')
        self.own = Transaction.objects.create(
            user=self.user, category=self.category,
            amount=Decimal('100.00'), date=timezone.localdate(), comment='Своя операция'
        )
        self.foreign_category = Category.objects.create(user=self.other, name='Еда', type='expense')
        self.foreign = Transaction.objects.create(
            user=self.other, category=self.foreign_category,
            amount=Decimal('200.00'), date=timezone.localdate(), comment='Чужая операция'
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse('transactions_list'))
        self.assertEqual(response.status_code, 302)

    def test_list_shows_only_own_transactions(self):
        self.client.login(username='alice', password='pass12345')
        response = self.client.get(reverse('transactions_list'))
        self.assertContains(response, 'Своя операция')
        self.assertNotContains(response, 'Чужая операция')

    def test_delete_foreign_transaction_returns_404(self):
        self.client.login(username='alice', password='pass12345')
        response = self.client.post(reverse('transaction_delete', args=[self.foreign.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=self.foreign.pk).exists())

    def test_category_with_transactions_is_not_deleted(self):
        self.client.login(username='alice', password='pass12345')
        response = self.client.post(reverse('category_delete', args=[self.category.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
        self.assertTrue(Transaction.objects.filter(pk=self.own.pk).exists())

    def test_filters_are_preserved_after_adding(self):
        self.client.login(username='alice', password='pass12345')
        response = self.client.post(
            reverse('transactions_list') + '?type=expense',
            {
                'category': self.category.pk,
                'amount': '50',
                'date': timezone.localdate().isoformat(),
                'comment': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        location = response['Location']
        self.assertIn('type=expense', location)
        self.assertIn('added=1', location)

    def test_analytics_uses_real_data(self):
        self.client.login(username='alice', password='pass12345')
        response = self.client.get(reverse('analytics'))
        self.assertEqual(response.status_code, 200)
        chart_data = response.context['chart_data']
        self.assertEqual(chart_data['category']['values'], [100.0])
        self.assertEqual(response.context['expense_total'], Decimal('100.00'))
        self.assertContains(response, 'Расходы по категориям')

    def test_analytics_periods_render(self):
        self.client.login(username='alice', password='pass12345')
        for period in ('month', 'quarter', 'year', 'all', 'unknown'):
            response = self.client.get(reverse('analytics'), {'period': period})
            self.assertEqual(response.status_code, 200, period)

    def test_dashboard_renders(self):
        self.client.login(username='alice', password='pass12345')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_categories_page_renders(self):
        self.client.login(username='alice', password='pass12345')
        response = self.client.get(reverse('categories_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Еда')

    def test_transaction_edit_page_renders(self):
        self.client.login(username='alice', password='pass12345')
        response = self.client.get(reverse('transaction_edit', args=[self.own.pk]))
        self.assertEqual(response.status_code, 200)


@override_settings(API_SECRET_KEY=API_KEY)
class FinanceApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.profile = Profile.objects.create(user=self.user, vk_id=777)
        self.expense = Category.objects.create(user=self.user, name='Еда', type='expense')
        self.income = Category.objects.create(user=self.user, name='Зарплата', type='income')

    def api_post(self, path, payload, key=API_KEY):
        headers = {'HTTP_X_API_KEY': key} if key else {}
        return self.client.post(
            path, data=json.dumps(payload), content_type='application/json', **headers
        )

    def test_api_requires_key(self):
        response = self.api_post(
            reverse('api_add'),
            {'vk_id': 777, 'amount': '10', 'category': 'Еда'},
            key=None,
        )
        self.assertEqual(response.status_code, 401)

    def test_rejects_invalid_amount(self):
        for amount in (0, -5, 'abc', None):
            response = self.api_post(
                reverse('api_add'),
                {'vk_id': 777, 'amount': amount, 'category': 'Еда'},
            )
            self.assertEqual(response.status_code, 400, amount)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_rejects_unknown_type(self):
        response = self.api_post(
            reverse('api_add'),
            {'vk_id': 777, 'amount': '10', 'category': 'Еда', 'type': 'gift'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_adds_transaction(self):
        response = self.api_post(
            reverse('api_add'),
            {'vk_id': 777, 'amount': '123.45', 'category': 'Еда', 'type': 'expense'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

        created = Transaction.objects.get()
        self.assertEqual(created.amount, Decimal('123.45'))
        self.assertEqual(created.source, 'vk')
        self.assertEqual(created.category.name, 'Еда')
        self.assertEqual(created.category.type, 'expense')

    def test_unlinked_vk_returns_404(self):
        response = self.api_post(
            reverse('api_add'),
            {'vk_id': 999, 'amount': '10', 'category': 'Еда'},
        )
        self.assertEqual(response.status_code, 404)

    def test_balance(self):
        Transaction.objects.create(
            user=self.user, category=self.income,
            amount=Decimal('1000.00'), date=timezone.localdate()
        )
        Transaction.objects.create(
            user=self.user, category=self.expense,
            amount=Decimal('500.00'), date=timezone.localdate()
        )
        response = self.api_post(reverse('api_balance'), {'vk_id': 777})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'balance': 500.0, 'income': 1000.0, 'expenses': 500.0},
        )

    def test_get_transactions(self):
        Transaction.objects.create(
            user=self.user, category=self.expense,
            amount=Decimal('42.00'), date=timezone.localdate(), comment='Обед'
        )
        response = self.client.get(
            reverse('api_transactions'), {'vk_id': 777}, HTTP_X_API_KEY=API_KEY
        )
        self.assertEqual(response.status_code, 200)
        items = response.json()['transactions']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['amount'], 42.0)
        self.assertEqual(items[0]['comment'], 'Обед')

    def test_link_vk_with_valid_code(self):
        user = User.objects.create_user('linker', password='pass12345')
        link = LinkCode.generate_for(user)
        response = self.api_post(reverse('api_link'), {'vk_id': 555, 'code': link.code})
        self.assertEqual(response.status_code, 200)
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.vk_id, 555)
        self.assertFalse(LinkCode.objects.filter(pk=link.pk).exists())

    def test_link_vk_with_expired_code(self):
        user = User.objects.create_user('linker', password='pass12345')
        link = LinkCode.generate_for(user)
        LinkCode.objects.filter(pk=link.pk).update(
            created_at=timezone.now() - timedelta(minutes=11)
        )
        response = self.api_post(reverse('api_link'), {'vk_id': 556, 'code': link.code})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LinkCode.objects.filter(pk=link.pk).exists())
        self.assertFalse(Profile.objects.filter(vk_id=556).exists())

    def test_link_vk_already_linked_returns_409(self):
        user = User.objects.create_user('linker', password='pass12345')
        link = LinkCode.generate_for(user)
        response = self.api_post(reverse('api_link'), {'vk_id': 777, 'code': link.code})
        self.assertEqual(response.status_code, 409)

from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    TYPE_CHOICES = [
        ('income', 'Доход'),
        ('expense', 'Расход'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField('Название', max_length=50)
    type = models.CharField('Тип', max_length=10, choices=TYPE_CHOICES)
    color = models.CharField('Цвет', max_length=7, default='#6366f1')
    icon = models.CharField('Иконка', max_length=30, blank=True, default='💰')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['type', 'name']
        # у одного пользователя не может быть двух категорий с одинаковым названием и типом
        unique_together = ('user', 'name', 'type')

    def __str__(self):
        return f'{self.icon} {self.name} ({self.get_type_display()})'


class Transaction(models.Model):
    SOURCE_CHOICES = [
        ('web', 'Сайт'),
        ('vk', 'ВК-бот'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField('Сумма', max_digits=10, decimal_places=2)
    date = models.DateField('Дата')
    comment = models.CharField('Комментарий', max_length=200, blank=True)
    source = models.CharField('Источник', max_length=10, choices=SOURCE_CHOICES, default='web')
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        ordering = ['-date', '-created_at']

    def __str__(self):
        sign = '+' if self.category.type == 'income' else '-'
        return f'{sign}{self.amount} ₽ — {self.category.name} ({self.date})'

    @property
    def is_income(self):
        return self.category.type == 'income'
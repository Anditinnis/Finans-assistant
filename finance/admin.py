from django.contrib import admin
from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'user', 'icon', 'color')
    list_filter = ('type',)
    search_fields = ('name', 'user__username')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'category', 'amount', 'date', 'source')
    list_filter = ('source', 'category__type', 'date')
    search_fields = ('comment', 'user__username')
    date_hierarchy = 'date'
    list_select_related = ('user', 'category')
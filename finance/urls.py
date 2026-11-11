from django.urls import path
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('transactions/', views.transactions_list, name='transactions_list'),
    path('transactions/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('categories/', views.categories_list, name='categories_list'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('analytics/', login_required(
        TemplateView.as_view(template_name='finance/analytics.html')
),  name='analytics'),
]
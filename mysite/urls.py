from django.contrib import admin
from django.urls import path, include
from accounts import views as account_views
from finance import api as finance_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', account_views.home_view, name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('accounts.urls')),
    path('finance/', include('finance.urls')),

    path('api/add/', finance_api.api_add_transaction, name='api_add'),
    path('api/balance/', finance_api.api_get_balance, name='api_balance'),
    path('api/link/', finance_api.api_link_vk, name='api_link'),
]
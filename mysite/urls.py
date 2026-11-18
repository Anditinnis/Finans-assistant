from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from accounts import views as account_views
from finance import api as finance_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', account_views.home_view, name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('accounts.urls')),
    path('finance/', include('finance.urls')),

    # API для бота (Django)
    path('api/add/', finance_api.api_add_transaction, name='api_add'),
    path('api/balance/', finance_api.api_get_balance, name='api_balance'),
    path('api/link/', finance_api.api_link_vk, name='api_link'),
    path('api/transactions/', finance_api.api_get_transactions, name='api_transactions'),
    path('api/users/by-vk/<int:vk_id>/', finance_api.api_get_user_by_vk, name='api_user_by_vk'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
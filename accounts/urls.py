from django.urls import path
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', login_required(
        TemplateView.as_view(template_name='profile.html')
    ), name='profile'),
    path('link-vk/', views.link_vk_page, name='link_vk'),
]
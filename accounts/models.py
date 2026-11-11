import secrets
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    vk_id = models.BigIntegerField('VK ID', null=True, blank=True, unique=True)

    def __str__(self):
        return f'Профиль {self.user.username}'


class LinkCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='link_codes')
    code = models.CharField('Код', max_length=16, unique=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    @classmethod
    def generate_for(cls, user):
        cls.objects.filter(user=user).delete()
        code = secrets.token_urlsafe(6)[:10]
        return cls.objects.create(user=user, code=code)

    def __str__(self):
        return f'{self.code} для {self.user.username}'
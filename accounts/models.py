from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    vk_id = models.BigIntegerField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f'Профиль {self.user.username}'


class LinkCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f'{self.code} для {self.user.username}'
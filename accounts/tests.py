from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import LinkCode, Profile


class RegistrationTests(TestCase):
    def test_register_creates_profile(self):
        response = self.client.post(reverse('register'), {
            'username': 'newbie',
            'email': 'newbie@example.com',
            'password1': 'StrongPass12345',
            'password2': 'StrongPass12345',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newbie')
        self.assertTrue(Profile.objects.filter(user=user).exists())


class LinkCodeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')

    def test_generate_replaces_previous_code(self):
        first = LinkCode.generate_for(self.user)
        second = LinkCode.generate_for(self.user)
        self.assertFalse(LinkCode.objects.filter(pk=first.pk).exists())
        self.assertTrue(LinkCode.objects.filter(pk=second.pk).exists())

    def test_is_expired(self):
        link = LinkCode.generate_for(self.user)
        self.assertFalse(link.is_expired())

        LinkCode.objects.filter(pk=link.pk).update(
            created_at=timezone.now() - timedelta(minutes=11)
        )
        link.refresh_from_db()
        self.assertTrue(link.is_expired())


class PublicPagesTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_renders(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_register_page_renders(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)


class ProfileAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.client.login(username='alice', password='pass12345')

    def test_profile_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

    def test_link_vk_page_generates_code(self):
        response = self.client.post(reverse('link_vk'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['code'])
        self.assertTrue(
            LinkCode.objects.filter(user=self.user, code=response.context['code']).exists()
        )

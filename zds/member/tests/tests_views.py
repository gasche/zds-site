# coding: utf-8

import urllib

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from zds.member.factories import ProfileFactory, StaffProfileFactory, NonAsciiProfileFactory
from zds.member.forms import RegisterForm, ChangeUserForm, ChangePasswordForm
from zds.member.models import Profile

from zds.member.models import TokenRegister, Ban


class MemberTests(TestCase):

    def setUp(self):
        settings.EMAIL_BACKEND = \
            'django.core.mail.backends.locmem.EmailBackend'
        self.mas = ProfileFactory()
        settings.BOT_ACCOUNT = self.mas.user.username

    def test_login(self):
        """To test user login."""
        user = ProfileFactory()

        result = self.client.post(
            reverse('zds.member.views.login_view'),
            {'username': user.user.username,
             'password': 'hostel',
             'remember': 'remember'},
            follow=False)
        # bad password then no redirection
        self.assertEqual(result.status_code, 200)

        result = self.client.post(
            reverse('zds.member.views.login_view'),
            {'username': user.user.username,
             'password': 'hostel77',
             'remember': 'remember'},
            follow=False)
        # good password then redirection
        self.assertEqual(result.status_code, 302)

    def test_register(self):
        """To test user registration."""

        result = self.client.post(
            reverse('zds.member.views.register_view'),
            {
                'username': 'firm1',
                'password': 'flavour',
                'password_confirm': 'flavour',
                'email': 'firm1@zestedesavoir.com'},
            follow=False)

        self.assertEqual(result.status_code, 200)

        # check email has been sent
        self.assertEquals(len(mail.outbox), 1)

        # clic on the link which has been sent in mail
        user = User.objects.get(username='firm1')
        self.assertFalse(user.is_active)

        token = TokenRegister.objects.get(user=user)
        result = self.client.get(
            settings.SITE_URL + token.get_absolute_url(),
            follow=False)

        self.assertEqual(result.status_code, 200)
        self.assertEquals(len(mail.outbox), 2)

        self.assertTrue(User.objects.get(username='firm1').is_active)

    def test_sanctions(self):
        """Test various sanctions."""

        staff = StaffProfileFactory()
        login_check = self.client.login(
            username=staff.user.username,
            password='hostel77')
        self.assertEqual(login_check, True)

        # Test: LS
        user_ls = ProfileFactory()
        result = self.client.post(
            reverse(
                'zds.member.views.modify_profile', kwargs={
                    'user_pk': user_ls.user.id}), {
                'ls': '', 'ls-text': 'Texte de test pour LS'}, follow=False)
        user = Profile.objects.get(id=user_ls.id)    # Refresh profile from DB
        self.assertEqual(result.status_code, 302)
        self.assertFalse(user.can_write)
        self.assertTrue(user.can_read)
        self.assertIsNone(user.end_ban_write)
        self.assertIsNone(user.end_ban_read)
        ban = Ban.objects.filter(user__id=user.user.id).order_by('-pubdate')[0]
        self.assertEqual(ban.type, 'Lecture Seule')
        self.assertEqual(ban.text, 'Texte de test pour LS')
        self.assertEquals(len(mail.outbox), 1)

        # Test: Un-LS
        result = self.client.post(
            reverse(
                'zds.member.views.modify_profile', kwargs={
                    'user_pk': user_ls.user.id}), {
                'un-ls': '', 'unls-text': 'Texte de test pour un-LS'},
            follow=False)
        user = Profile.objects.get(id=user_ls.id)    # Refresh profile from DB
        self.assertEqual(result.status_code, 302)
        self.assertTrue(user.can_write)
        self.assertTrue(user.can_read)
        self.assertIsNone(user.end_ban_write)
        self.assertIsNone(user.end_ban_read)
        ban = Ban.objects.filter(user__id=user.user.id).order_by('-id')[0]
        self.assertEqual(ban.type, u'Autorisation d\'écrire')
        self.assertEqual(ban.text, 'Texte de test pour un-LS')
        self.assertEquals(len(mail.outbox), 2)

        # Test: LS temp
        user_ls_temp = ProfileFactory()
        result = self.client.post(
            reverse(
                'zds.member.views.modify_profile', kwargs={
                    'user_pk': user_ls_temp.user.id}), {
                'ls-temp': '', 'ls-jrs': 10,
                'ls-temp-text': 'Texte de test pour LS TEMP'},
            follow=False)
        user = Profile.objects.get(
            id=user_ls_temp.id)    # Refresh profile from DB
        self.assertEqual(result.status_code, 302)
        self.assertFalse(user.can_write)
        self.assertTrue(user.can_read)
        self.assertIsNotNone(user.end_ban_write)
        self.assertIsNone(user.end_ban_read)
        ban = Ban.objects.filter(user__id=user.user.id).order_by('-id')[0]
        self.assertEqual(ban.type, 'Lecture Seule Temporaire')
        self.assertEqual(ban.text, 'Texte de test pour LS TEMP')
        self.assertEquals(len(mail.outbox), 3)

        # Test: BAN
        user_ban = ProfileFactory()
        result = self.client.post(
            reverse(
                'zds.member.views.modify_profile', kwargs={
                    'user_pk': user_ban.user.id}), {
                'ban': '', 'ban-text': 'Texte de test pour BAN'}, follow=False)
        user = Profile.objects.get(id=user_ban.id)    # Refresh profile from DB
        self.assertEqual(result.status_code, 302)
        self.assertTrue(user.can_write)
        self.assertFalse(user.can_read)
        self.assertIsNone(user.end_ban_write)
        self.assertIsNone(user.end_ban_read)
        ban = Ban.objects.filter(user__id=user.user.id).order_by('-id')[0]
        self.assertEqual(ban.type, u'Ban définitif')
        self.assertEqual(ban.text, 'Texte de test pour BAN')
        self.assertEquals(len(mail.outbox), 4)

        # Test: un-BAN
        result = self.client.post(
            reverse(
                'zds.member.views.modify_profile', kwargs={
                    'user_pk': user_ban.user.id}),
            {'un-ban': '',
             'unban-text': 'Texte de test pour BAN'},
            follow=False)
        user = Profile.objects.get(id=user_ban.id)    # Refresh profile from DB
        self.assertEqual(result.status_code, 302)
        self.assertTrue(user.can_write)
        self.assertTrue(user.can_read)
        self.assertIsNone(user.end_ban_write)
        self.assertIsNone(user.end_ban_read)
        ban = Ban.objects.filter(user__id=user.user.id).order_by('-id')[0]
        self.assertEqual(ban.type, 'Autorisation de se connecter')
        self.assertEqual(ban.text, 'Texte de test pour BAN')
        self.assertEquals(len(mail.outbox), 5)

        # Test: BAN temp
        user_ban_temp = ProfileFactory()
        result = self.client.post(
            reverse('zds.member.views.modify_profile',
                    kwargs={'user_pk': user_ban_temp.user.id}),
            {'ban-temp': '', 'ban-jrs': 10,
             'ban-temp-text': 'Texte de test pour BAN TEMP'},
            follow=False)
        user = Profile.objects.get(
            id=user_ban_temp.id)    # Refresh profile from DB
        self.assertEqual(result.status_code, 302)
        self.assertTrue(user.can_write)
        self.assertFalse(user.can_read)
        self.assertIsNone(user.end_ban_write)
        self.assertIsNotNone(user.end_ban_read)
        ban = Ban.objects.filter(user__id=user.user.id).order_by('-id')[0]
        self.assertEqual(ban.type, 'Ban Temporaire')
        self.assertEqual(ban.text, 'Texte de test pour BAN TEMP')
        self.assertEquals(len(mail.outbox), 6)

    def test_nonascii(self):
        user = NonAsciiProfileFactory()
        result = self.client.get(reverse('zds.member.views.login_view') + '?next='
                                        + reverse('zds.member.views.details', args=[user.user.username]),
                                 follow=False)
        self.assertEqual(result.status_code, 200)


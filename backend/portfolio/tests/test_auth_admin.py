"""Tests for the Unfold-styled User/Group admin re-registrations."""

from django.contrib.admin.sites import site
from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from unfold.admin import ModelAdmin
from unfold.forms import UserChangeForm, UserCreationForm


class AuthAdminUnfoldStylingTests(TestCase):
    def test_user_admin_uses_unfold_model_admin(self):
        self.assertIsInstance(site._registry[User], ModelAdmin)

    def test_group_admin_uses_unfold_model_admin(self):
        self.assertIsInstance(site._registry[Group], ModelAdmin)

    def test_user_admin_uses_unfold_change_form(self):
        self.assertIs(site._registry[User].form, UserChangeForm)

    def test_user_admin_uses_unfold_creation_form(self):
        self.assertIs(site._registry[User].add_form, UserCreationForm)


class AuthAdminPagesRenderTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="ad@x.test", password="x",
            is_staff=True, is_superuser=True,
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_user_list_renders(self):
        r = self.client.get("/admin/auth/user/")
        self.assertEqual(r.status_code, 200)

    def test_group_list_renders(self):
        r = self.client.get("/admin/auth/group/")
        self.assertEqual(r.status_code, 200)

    def test_user_change_form_renders(self):
        r = self.client.get(f"/admin/auth/user/{self.admin.pk}/change/")
        self.assertEqual(r.status_code, 200)

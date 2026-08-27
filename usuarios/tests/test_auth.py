"""Tests for user registration, authentication and profile APIs."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from usuarios.services import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    login_user,
    register_user,
)

User = get_user_model()


class RegisterUserServiceTests(TestCase):
    def test_register_user_creates_account(self):
        user = register_user(
            username="alice",
            email="alice@example.com",
            password="Str0ng-Pass!",
        )
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.email, "alice@example.com")
        self.assertTrue(user.check_password("Str0ng-Pass!"))

    def test_register_duplicate_username_raises(self):
        register_user(
            username="alice",
            email="alice@example.com",
            password="Str0ng-Pass!",
        )
        with self.assertRaises(UserAlreadyExistsError):
            register_user(
                username="alice",
                email="outra@example.com",
                password="Str0ng-Pass!",
            )

    def test_register_duplicate_email_raises(self):
        register_user(
            username="alice",
            email="alice@example.com",
            password="Str0ng-Pass!",
        )
        with self.assertRaises(UserAlreadyExistsError):
            register_user(
                username="bob",
                email="alice@example.com",
                password="Str0ng-Pass!",
            )


class AuthAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "Str0ng-Pass!"
        self.user = register_user(
            username="alice",
            email="alice@example.com",
            password=self.password,
        )

    def test_cadastro_api(self):
        response = self.client.post(
            reverse("api-usuarios-cadastro"),
            {
                "username": "bob",
                "email": "bob@example.com",
                "password": self.password,
                "password_confirm": self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "bob")
        self.assertTrue(User.objects.filter(username="bob").exists())

    def test_login_api_success(self):
        response = self.client.post(
            reverse("api-usuarios-login"),
            {"username": "alice", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "alice")
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_api_invalid_credentials(self):
        response = self.client.post(
            reverse("api-usuarios-login"),
            {"username": "alice", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_perfil_requires_authentication(self):
        response = self.client.get(reverse("api-usuarios-perfil"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_perfil_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("api-usuarios-perfil"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "alice@example.com")

    def test_perfil_update(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("api-usuarios-perfil"),
            {"first_name": "Alice", "last_name": "Silva"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alice")
        self.assertEqual(self.user.last_name, "Silva")

    def test_logout_api(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("api-usuarios-logout"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("_auth_user_id", self.client.session)


class LoginServiceTests(TestCase):
    def setUp(self):
        self.password = "Str0ng-Pass!"
        self.user = register_user(
            username="alice",
            email="alice@example.com",
            password=self.password,
        )

    def test_login_user_invalid(self):
        from django.test import RequestFactory

        request = RequestFactory().post("/api/usuarios/login/")
        request.session = self.client.session
        with self.assertRaises(InvalidCredentialsError):
            login_user(request, username="alice", password="nope")

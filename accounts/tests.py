from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class RegistrationTests(TestCase):
    """Tests for POST /api/auth/register/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/register/"

    def test_register_success(self):
        resp = self.client.post(
            self.url,
            {"username": "newuser", "email": "new@example.com", "password": "strongpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["username"], "newuser")
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_creates_profile(self):
        self.client.post(
            self.url,
            {"username": "profuser", "password": "strongpass123"},
            format="json",
        )
        user = User.objects.get(username="profuser")
        self.assertTrue(hasattr(user, "profile"))
        self.assertFalse(user.profile.is_online)

    def test_register_duplicate_username(self):
        User.objects.create_user(username="taken", password="pass12345678")
        resp = self.client.post(
            self.url,
            {"username": "taken", "password": "strongpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        resp = self.client.post(
            self.url,
            {"username": "short", "password": "abc"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(TestCase):
    """Tests for POST /api/auth/login/ (JWT token obtain)"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="loginuser", password="testpass1234")
        self.url = "/api/auth/login/"

    def test_login_returns_tokens(self):
        resp = self.client.post(
            self.url,
            {"username": "loginuser", "password": "testpass1234"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_login_invalid_credentials(self):
        resp = self.client.post(
            self.url,
            {"username": "loginuser", "password": "wrong"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class UserListTests(TestCase):
    """Tests for GET /api/auth/users/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="me", password="testpass1234")
        User.objects.create_user(username="other", password="testpass1234")
        self.client.force_authenticate(user=self.user)

    def test_list_users_authenticated(self):
        resp = self.client.get("/api/auth/users/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        usernames = [u["username"] for u in resp.data]
        self.assertIn("me", usernames)
        self.assertIn("other", usernames)

    def test_list_users_contains_online_field(self):
        resp = self.client.get("/api/auth/users/")
        self.assertIn("is_online", resp.data[0])

    def test_list_users_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get("/api/auth/users/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class UserDetailTests(TestCase):
    """Tests for GET /api/auth/users/<pk>/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="me", password="testpass1234")
        self.other = User.objects.create_user(username="other", password="testpass1234")
        self.client.force_authenticate(user=self.user)

    def test_detail_success(self):
        resp = self.client.get(f"/api/auth/users/{self.other.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "other")

    def test_detail_not_found(self):
        resp = self.client.get("/api/auth/users/99999/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

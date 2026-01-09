"""
Tests for AuthenticationProfile CRUD operations and authentication behavior.
"""
import base64
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, ResponseHandler, AuthenticationProfile

User = get_user_model()


class AuthenticationProfileCRUDTests(TestCase):
    """Tests for creating, updating, and deleting authentication profiles."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.api_base = '/_mokkapi_api/api'

    # --- Create API Key Profile ---
    def test_create_api_key_profile(self):
        """Create an API key authentication profile."""
        response = self.client.post(
            f"{self.api_base}/auth-profiles/",
            data=json.dumps({
                "name": "Test API Key Profile",
                "auth_type": "API_KEY"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(AuthenticationProfile.objects.filter(name="Test API Key Profile").exists())

    def test_create_api_key_profile_auto_generates_key(self):
        """API key is auto-generated if not provided."""
        profile = AuthenticationProfile.objects.create(
            name="Auto Key Profile",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        self.assertIsNotNone(profile.api_key)
        self.assertTrue(len(profile.api_key) > 20)

    def test_create_api_key_profile_with_custom_key(self):
        """Can provide a custom API key on creation."""
        custom_key = "my-custom-api-key-12345"
        profile = AuthenticationProfile(
            name="Custom Key Profile",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            api_key=custom_key,
            owner=self.user
        )
        profile.save()
        self.assertEqual(profile.api_key, custom_key)

    # --- Create Basic Auth Profile ---
    def test_create_basic_auth_profile(self):
        """Create a basic auth profile with username and password."""
        profile = AuthenticationProfile(
            name="Basic Auth Profile",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        profile.set_password("secretpass")
        profile.save()
        self.assertEqual(profile.basic_auth_username, "apiuser")
        self.assertTrue(profile.check_password("secretpass"))

    def test_create_basic_auth_profile_password_is_hashed(self):
        """Password is stored hashed, not plaintext."""
        profile = AuthenticationProfile(
            name="Hashed Password Profile",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        profile.set_password("mypassword")
        profile.save()
        self.assertNotEqual(profile.basic_auth_password_hash, "mypassword")
        self.assertTrue(profile.basic_auth_password_hash.startswith("pbkdf2_sha256$") or
                       profile.basic_auth_password_hash.startswith("argon2"))

    def test_create_basic_auth_without_password_fails(self):
        """Basic auth profile requires a password."""
        profile = AuthenticationProfile(
            name="No Password Profile",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        self.assertFalse(profile.check_password("anything"))

    # --- Update Profile ---
    def test_update_api_key(self):
        """Update/regenerate an API key."""
        profile = AuthenticationProfile.objects.create(
            name="Regen Key Profile",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        old_key = profile.api_key
        profile.generate_api_key()
        profile.save()
        self.assertNotEqual(profile.api_key, old_key)

    def test_update_basic_auth_password(self):
        """Update basic auth password."""
        profile = AuthenticationProfile(
            name="Update Password Profile",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        profile.set_password("oldpassword")
        profile.save()

        profile.set_password("newpassword")
        profile.save()

        self.assertFalse(profile.check_password("oldpassword"))
        self.assertTrue(profile.check_password("newpassword"))

    def test_update_profile_name(self):
        """Update profile name."""
        profile = AuthenticationProfile.objects.create(
            name="Old Name",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        response = self.client.patch(
            f"{self.api_base}/auth-profiles/{profile.id}/",
            data=json.dumps({"name": "New Name"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.name, "New Name")

    def test_change_auth_type_clears_incompatible_fields(self):
        """Changing auth type clears fields from previous type."""
        profile = AuthenticationProfile.objects.create(
            name="Type Change Profile",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        old_key = profile.api_key
        self.assertIsNotNone(old_key)

        profile.auth_type = AuthenticationProfile.AuthType.BASIC
        profile.basic_auth_username = "newuser"
        profile.set_password("newpass")
        profile.save()

        self.assertIsNone(profile.api_key)

    # --- Delete Profile ---
    def test_delete_profile_via_api(self):
        """Delete an authentication profile via REST API."""
        profile = AuthenticationProfile.objects.create(
            name="Delete Me Profile",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        profile_id = profile.id
        response = self.client.delete(f"{self.api_base}/auth-profiles/{profile_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(AuthenticationProfile.objects.filter(id=profile_id).exists())

    def test_delete_profile_clears_endpoint_auth(self):
        """Deleting profile sets endpoint.authentication to null."""
        profile = AuthenticationProfile.objects.create(
            name="Endpoint Auth Profile",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        endpoint = MockEndpoint.objects.create(
            path="test/auth-delete",
            authentication=profile,
            owner=self.user,
            creator=self.user
        )
        profile.delete()
        endpoint.refresh_from_db()
        self.assertIsNone(endpoint.authentication)

    def test_delete_nonexistent_profile_returns_404(self):
        """Deleting a profile that doesn't exist returns 404."""
        response = self.client.delete(f"{self.api_base}/auth-profiles/99999/")
        self.assertEqual(response.status_code, 404)


class AuthenticationBehaviorTests(TestCase):
    """Tests for authentication enforcement on mock endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.endpoint = MockEndpoint.objects.create(
            path="test/auth",
            owner=self.user,
            creator=self.user
        )
        self.handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"status": "ok"}'
        )

    # --- API Key Auth ---
    def test_api_key_auth_valid_key_succeeds(self):
        """Request with valid API key in X-API-Key header succeeds."""
        auth_profile = AuthenticationProfile.objects.create(
            name="Test API Key",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY=auth_profile.api_key
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_api_key_auth_invalid_key_returns_401(self):
        """Request with invalid API key returns 401."""
        auth_profile = AuthenticationProfile.objects.create(
            name="Test API Key",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY="invalid-key-12345"
        )
        self.assertEqual(response.status_code, 401)

    def test_api_key_auth_missing_key_returns_401(self):
        """Request without API key header returns 401."""
        auth_profile = AuthenticationProfile.objects.create(
            name="Test API Key",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 401)

    def test_api_key_auth_empty_key_returns_401(self):
        """Request with empty API key header returns 401."""
        auth_profile = AuthenticationProfile.objects.create(
            name="Test API Key",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY=""
        )
        self.assertEqual(response.status_code, 401)

    # --- Basic Auth ---
    def test_basic_auth_valid_credentials_succeeds(self):
        """Request with valid Basic auth credentials succeeds."""
        auth_profile = AuthenticationProfile(
            name="Test Basic Auth",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        auth_profile.set_password("secretpass")
        auth_profile.save()
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        credentials = base64.b64encode(b"apiuser:secretpass").decode("utf-8")
        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_AUTHORIZATION=f"Basic {credentials}"
        )
        self.assertEqual(response.status_code, 200)

    def test_basic_auth_invalid_password_returns_401(self):
        """Request with wrong password returns 401."""
        auth_profile = AuthenticationProfile(
            name="Test Basic Auth",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        auth_profile.set_password("secretpass")
        auth_profile.save()
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        credentials = base64.b64encode(b"apiuser:wrongpassword").decode("utf-8")
        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_AUTHORIZATION=f"Basic {credentials}"
        )
        self.assertEqual(response.status_code, 401)

    def test_basic_auth_invalid_username_returns_401(self):
        """Request with wrong username returns 401."""
        auth_profile = AuthenticationProfile(
            name="Test Basic Auth",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        auth_profile.set_password("secretpass")
        auth_profile.save()
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        credentials = base64.b64encode(b"wronguser:secretpass").decode("utf-8")
        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_AUTHORIZATION=f"Basic {credentials}"
        )
        self.assertEqual(response.status_code, 401)

    def test_basic_auth_missing_header_returns_401(self):
        """Request without Authorization header returns 401."""
        auth_profile = AuthenticationProfile(
            name="Test Basic Auth",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        auth_profile.set_password("secretpass")
        auth_profile.save()
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 401)

    def test_basic_auth_malformed_header_returns_401(self):
        """Request with malformed Authorization header returns 401."""
        auth_profile = AuthenticationProfile(
            name="Test Basic Auth",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        auth_profile.set_password("secretpass")
        auth_profile.save()
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_AUTHORIZATION="Basic not-valid-base64!!!"
        )
        self.assertEqual(response.status_code, 401)

    def test_basic_auth_wrong_scheme_returns_401(self):
        """Request with Bearer instead of Basic returns 401."""
        auth_profile = AuthenticationProfile(
            name="Test Basic Auth",
            auth_type=AuthenticationProfile.AuthType.BASIC,
            basic_auth_username="apiuser",
            owner=self.user
        )
        auth_profile.set_password("secretpass")
        auth_profile.save()
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_AUTHORIZATION="Bearer some-token-here"
        )
        self.assertEqual(response.status_code, 401)

    # --- Attaching/Detaching Auth ---
    def test_attach_auth_to_endpoint(self):
        """Attach authentication profile to previously public endpoint."""
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)

        auth_profile = AuthenticationProfile.objects.create(
            name="Attach Test Profile",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 401)

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY=auth_profile.api_key
        )
        self.assertEqual(response.status_code, 200)

    def test_detach_auth_from_endpoint(self):
        """Remove authentication from protected endpoint (make public)."""
        auth_profile = AuthenticationProfile.objects.create(
            name="Detach Test Profile",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        self.endpoint.authentication = auth_profile
        self.endpoint.save()

        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 401)

        self.endpoint.authentication = None
        self.endpoint.save()

        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)

    def test_change_endpoint_auth_profile(self):
        """Switch endpoint from one auth profile to another."""
        profile1 = AuthenticationProfile.objects.create(
            name="Profile One",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )
        profile2 = AuthenticationProfile.objects.create(
            name="Profile Two",
            auth_type=AuthenticationProfile.AuthType.API_KEY,
            owner=self.user
        )

        self.endpoint.authentication = profile1
        self.endpoint.save()

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY=profile1.api_key
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY=profile2.api_key
        )
        self.assertEqual(response.status_code, 401)

        self.endpoint.authentication = profile2
        self.endpoint.save()

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY=profile2.api_key
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY=profile1.api_key
        )
        self.assertEqual(response.status_code, 401)

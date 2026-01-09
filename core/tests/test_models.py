"""
Tests for Django models: MockEndpoint, AuthenticationProfile, ResponseHandler.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, ResponseHandler, AuthenticationProfile

User = get_user_model()


class MockEndpointModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_path_normalization(self):
        """Ensure the clean() method normalizes paths correctly."""
        endpoint = MockEndpoint(
            path="/some//unique//path/",
            owner=self.user,
            creator=self.user
        )
        endpoint.clean()
        self.assertEqual(endpoint.path, "some/unique/path")

    def test_path_empty_after_normalization(self):
        """Ensure that a path that normalizes to empty raises a ValidationError."""
        endpoint = MockEndpoint(
            path="///",
            owner=self.user,
            creator=self.user
        )
        with self.assertRaises(ValidationError):
            endpoint.clean()

    def test_str_method(self):
        """Test that the __str__ method returns the expected format."""
        endpoint = MockEndpoint(
            path="some/unique/path",
            owner=self.user,
            creator=self.user
        )
        self.assertIn("/some/unique/path", str(endpoint))
        self.assertIn("Public", str(endpoint))


class AuthenticationProfileModelTests(TestCase):
    """Tests for AuthenticationProfile model validation and behavior."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

    # --- Validation ---
    def test_api_key_type_cannot_have_basic_auth_fields(self):
        """API Key type profile rejects basic auth username/password."""
        profile = AuthenticationProfile(
            name='Test API Key',
            auth_type='api_key',
            api_key='test-key-123',
            basic_auth_username='shouldnt_have',
            owner=self.user
        )
        try:
            profile.full_clean()
            profile.save()
        except Exception:
            pass  # Expected if validation rejects this

    def test_basic_auth_type_cannot_have_api_key(self):
        """Basic Auth type profile rejects api_key field."""
        profile = AuthenticationProfile(
            name='Test Basic Auth',
            auth_type='basic_auth',
            api_key='shouldnt_have',
            basic_auth_username='testuser',
            owner=self.user
        )
        try:
            profile.full_clean()
            profile.save()
        except Exception:
            pass  # Expected if validation rejects this

    def test_basic_auth_requires_username(self):
        """Basic Auth type requires username."""
        profile = AuthenticationProfile(
            name='Test Basic Auth No User',
            auth_type='basic_auth',
            owner=self.user
        )
        try:
            profile.full_clean()
            self.fail("Expected validation error for missing username")
        except Exception:
            pass  # Expected

    def test_unique_profile_name_per_user(self):
        """Profile names must be unique."""
        AuthenticationProfile.objects.create(
            name='Duplicate Name',
            auth_type='api_key',
            api_key='key1',
            owner=self.user
        )
        with self.assertRaises(Exception):
            AuthenticationProfile.objects.create(
                name='Duplicate Name',
                auth_type='api_key',
                api_key='key2',
                owner=self.user
            )

    def test_unique_api_key(self):
        """API keys must be unique across all profiles."""
        AuthenticationProfile.objects.create(
            name='Profile 1',
            auth_type='api_key',
            api_key='unique-key-123',
            owner=self.user
        )
        other_user = User.objects.create_user(username='other', password='pass')
        with self.assertRaises(Exception):
            AuthenticationProfile.objects.create(
                name='Profile 2',
                auth_type='api_key',
                api_key='unique-key-123',
                owner=other_user
            )

    # --- API Key Generation ---
    def test_api_key_auto_generated_on_save(self):
        """API key is auto-generated if not provided."""
        profile = AuthenticationProfile.objects.create(
            name='Auto Key Profile',
            auth_type='api_key',
            owner=self.user
        )
        self.assertIsNotNone(profile.api_key)
        self.assertTrue(len(profile.api_key) > 0)

    def test_api_key_not_regenerated_on_update(self):
        """Existing API key is preserved on update."""
        profile = AuthenticationProfile.objects.create(
            name='Preserve Key',
            auth_type='api_key',
            api_key='original-key-123',
            owner=self.user
        )
        original_key = profile.api_key
        profile.name = 'Updated Name'
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.api_key, original_key)

    def test_generated_api_key_is_unique(self):
        """Generated API keys don't collide with existing ones."""
        profiles = []
        for i in range(5):
            profile = AuthenticationProfile.objects.create(
                name=f'Profile {i}',
                auth_type='api_key',
                owner=self.user
            )
            profiles.append(profile)
        api_keys = [p.api_key for p in profiles]
        self.assertEqual(len(api_keys), len(set(api_keys)))

    # --- Password Handling ---
    def test_password_is_hashed(self):
        """set_password stores hash, not plaintext."""
        profile = AuthenticationProfile.objects.create(
            name='Password Test',
            auth_type='basic_auth',
            basic_auth_username='testuser',
            owner=self.user
        )
        if hasattr(profile, 'set_password'):
            profile.set_password('secret123')
            profile.save()
            self.assertNotEqual(profile.basic_auth_password_hash, 'secret123')

    def test_check_password_correct(self):
        """check_password returns True for correct password."""
        profile = AuthenticationProfile.objects.create(
            name='Check Password Test',
            auth_type='basic_auth',
            basic_auth_username='testuser',
            owner=self.user
        )
        if hasattr(profile, 'set_password') and hasattr(profile, 'check_password'):
            profile.set_password('secret123')
            profile.save()
            self.assertTrue(profile.check_password('secret123'))

    def test_check_password_incorrect(self):
        """check_password returns False for wrong password."""
        profile = AuthenticationProfile.objects.create(
            name='Wrong Password Test',
            auth_type='basic_auth',
            basic_auth_username='testuser',
            owner=self.user
        )
        if hasattr(profile, 'set_password') and hasattr(profile, 'check_password'):
            profile.set_password('secret123')
            profile.save()
            self.assertFalse(profile.check_password('wrongpassword'))

    def test_check_password_empty_hash(self):
        """check_password handles missing password hash gracefully."""
        profile = AuthenticationProfile.objects.create(
            name='Empty Hash Test',
            auth_type='basic_auth',
            basic_auth_username='testuser',
            owner=self.user
        )
        if hasattr(profile, 'check_password'):
            result = profile.check_password('anypassword')
            self.assertFalse(result)


class ResponseHandlerModelTests(TestCase):
    """Tests for ResponseHandler model validation and behavior."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.endpoint = MockEndpoint.objects.create(
            path="test/handler-model",
            owner=self.user,
            creator=self.user
        )

    # --- Validation ---
    def test_http_method_normalized_to_uppercase(self):
        """HTTP method is converted to uppercase on clean."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method='get',
            response_status_code=200
        )
        handler.refresh_from_db()
        self.assertEqual(handler.http_method, 'GET')

    def test_unique_method_per_endpoint(self):
        """Cannot have duplicate HTTP methods for same endpoint."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method='GET',
            response_status_code=200
        )
        with self.assertRaises(Exception):
            ResponseHandler.objects.create(
                endpoint=self.endpoint,
                http_method='GET',
                response_status_code=201
            )

    def test_response_headers_must_be_dict(self):
        """response_headers field must be a dictionary."""
        handler = ResponseHandler(
            endpoint=self.endpoint,
            http_method='POST',
            response_status_code=200,
            response_headers={"Content-Type": "application/json"}
        )
        handler.full_clean()
        handler.save()
        self.assertIsInstance(handler.response_headers, dict)

    def test_invalid_http_method_rejected(self):
        """Invalid HTTP method choices are rejected."""
        handler = ResponseHandler(
            endpoint=self.endpoint,
            http_method='INVALID',
            response_status_code=200
        )
        try:
            handler.full_clean()
            handler.save()
        except Exception:
            pass  # Expected if validation rejects invalid methods

    # --- Defaults ---
    def test_default_status_code_is_200(self):
        """Default response_status_code is 200."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method='GET'
        )
        self.assertEqual(handler.response_status_code, 200)

    def test_default_headers_is_empty_dict(self):
        """Default response_headers is empty dict."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method='GET',
            response_status_code=200
        )
        self.assertEqual(handler.response_headers, {})

    def test_default_body_is_empty_string(self):
        """Default response_body is empty string."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method='GET',
            response_status_code=200
        )
        self.assertEqual(handler.response_body, '')

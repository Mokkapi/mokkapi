"""
Tests for concurrent access and state management.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, ResponseHandler, AuthenticationProfile

User = get_user_model()


class ConcurrencyTests(TestCase):
    """Tests for concurrent access and state management."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_endpoint_update_reflected_immediately(self):
        """Changes to endpoint are reflected in next request."""
        endpoint = MockEndpoint.objects.create(
            path='api/concurrency-test',
            owner=self.user,
            creator=self.user,
            description='Original'
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"version": 1}'
        )
        # First request
        response1 = self.client.get('/api/concurrency-test')
        self.assertEqual(response1.status_code, 200)

        # Update endpoint description
        endpoint.description = 'Updated'
        endpoint.save()

        # Next request should see the change
        response2 = self.client.get('/api/concurrency-test')
        self.assertEqual(response2.status_code, 200)

    def test_handler_update_reflected_immediately(self):
        """Changes to handler are reflected in next request."""
        endpoint = MockEndpoint.objects.create(
            path='api/handler-change',
            owner=self.user,
            creator=self.user
        )
        handler = ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"version": 1}'
        )
        # First request
        response1 = self.client.get('/api/handler-change')
        self.assertEqual(response1.status_code, 200)
        self.assertIn(b'version', response1.content)

        # Update handler
        handler.response_body = '{"version": 2}'
        handler.save()

        # Next request should see updated response
        response2 = self.client.get('/api/handler-change')
        self.assertEqual(response2.status_code, 200)
        self.assertIn(b'version', response2.content)
        self.assertIn(b'2', response2.content)

    def test_auth_change_reflected_immediately(self):
        """Auth profile changes are reflected in next request."""
        auth_profile = AuthenticationProfile.objects.create(
            name='Changing Auth',
            auth_type='api_key',
            api_key='original-key',
            owner=self.user
        )
        endpoint = MockEndpoint.objects.create(
            path='api/auth-change',
            owner=self.user,
            creator=self.user,
            authentication=auth_profile
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"protected": true}'
        )
        # Request with original key should work
        response1 = self.client.get(
            '/api/auth-change',
            HTTP_X_API_KEY='original-key'
        )
        self.assertEqual(response1.status_code, 200)

        # Change the API key
        auth_profile.api_key = 'new-key'
        auth_profile.save()

        # Old key should now fail
        response2 = self.client.get(
            '/api/auth-change',
            HTTP_X_API_KEY='original-key'
        )
        self.assertEqual(response2.status_code, 401)

        # New key should work
        response3 = self.client.get(
            '/api/auth-change',
            HTTP_X_API_KEY='new-key'
        )
        self.assertEqual(response3.status_code, 200)

    def test_duplicate_path_create_fails_atomically(self):
        """Concurrent creates with same path - one fails cleanly."""
        # Create first endpoint
        MockEndpoint.objects.create(
            path='api/unique-path',
            owner=self.user,
            creator=self.user
        )
        # Attempting to create duplicate should fail
        with self.assertRaises(Exception):
            MockEndpoint.objects.create(
                path='api/unique-path',
                owner=self.user,
                creator=self.user
            )

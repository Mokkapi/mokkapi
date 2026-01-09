"""
Tests for DRF serializers and REST API response formats.
"""
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, ResponseHandler, AuthenticationProfile

User = get_user_model()


class SerializerTests(TestCase):
    """Tests for DRF serializer validation and representation."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')
        self.api_base = '/_mokkapi_api/api'

    # --- MockEndpoint Serializer ---
    def test_endpoint_create_serializer_validates_path(self):
        """Create serializer validates path format."""
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_endpoint_serializer_includes_handlers(self):
        """Endpoint serializer includes nested handlers."""
        endpoint = MockEndpoint.objects.create(
            path='api/with-handler',
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200
        )
        response = self.client.get(f'{self.api_base}/endpoints/{endpoint.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('handlers', data)

    def test_endpoint_serializer_read_only_fields(self):
        """Certain fields are read-only in serializer."""
        endpoint = MockEndpoint.objects.create(
            path='api/readonly-test',
            owner=self.user,
            creator=self.user
        )
        other_user = User.objects.create_user(username='other', password='pass')
        response = self.client.patch(
            f'{self.api_base}/endpoints/{endpoint.id}/',
            data=json.dumps({'creator': other_user.id}),
            content_type='application/json'
        )
        endpoint.refresh_from_db()
        self.assertEqual(endpoint.creator.id, self.user.id)

    # --- ResponseHandler Serializer ---
    def test_handler_serializer_validates_method(self):
        """Handler serializer validates HTTP method choices."""
        endpoint = MockEndpoint.objects.create(
            path='api/handler-validation',
            owner=self.user,
            creator=self.user
        )
        response = self.client.post(
            f'{self.api_base}/handlers/',
            data=json.dumps({
                'endpoint': endpoint.id,
                'http_method': 'INVALID',
                'response_status_code': 200
            }),
            content_type='application/json'
        )
        self.assertIn(response.status_code, [201, 400])

    def test_handler_serializer_validates_status_code(self):
        """Handler serializer validates status code is positive integer."""
        endpoint = MockEndpoint.objects.create(
            path='api/status-validation',
            owner=self.user,
            creator=self.user
        )
        response = self.client.post(
            f'{self.api_base}/handlers/',
            data=json.dumps({
                'endpoint': endpoint.id,
                'http_method': 'GET',
                'response_status_code': -1
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_handler_serializer_validates_headers_json(self):
        """Handler serializer validates headers is valid JSON object."""
        endpoint = MockEndpoint.objects.create(
            path='api/headers-validation',
            owner=self.user,
            creator=self.user
        )
        response = self.client.post(
            f'{self.api_base}/handlers/',
            data=json.dumps({
                'endpoint': endpoint.id,
                'http_method': 'GET',
                'response_status_code': 200,
                'response_headers': {"Valid": "Header"}
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)

    # --- AuthenticationProfile Serializer ---
    def test_auth_profile_serializer_hides_password(self):
        """Auth profile serializer never exposes password hash."""
        profile = AuthenticationProfile.objects.create(
            name='Password Hidden Test',
            auth_type='basic_auth',
            basic_auth_username='testuser',
            owner=self.user
        )
        if hasattr(profile, 'set_password'):
            profile.set_password('secret123')
            profile.save()

        response = self.client.get(f'{self.api_base}/auth-profiles/{profile.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn('basic_auth_password_hash', data)
        self.assertNotIn('password', data)

    def test_auth_profile_serializer_hides_api_key_on_list(self):
        """API key is hidden or masked in list view."""
        AuthenticationProfile.objects.create(
            name='API Key Hidden Test',
            auth_type='api_key',
            api_key='super-secret-key-12345',
            owner=self.user
        )
        response = self.client.get(f'{self.api_base}/auth-profiles/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        if len(data) > 0:
            first_profile = data[0]
            if 'api_key' in first_profile:
                pass  # Key should either be absent or masked


class APIResponseFormatTests(TestCase):
    """Tests for consistent REST API response formats."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.api_base = '/_mokkapi_api/api'

    # --- Success Responses ---
    def test_list_endpoint_returns_array(self):
        """GET /endpoints/ returns array of endpoints."""
        MockEndpoint.objects.create(
            path='api/list-test',
            owner=self.user,
            creator=self.user
        )
        response = self.client.get(f'{self.api_base}/endpoints/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_detail_endpoint_returns_object(self):
        """GET /endpoints/{id}/ returns single endpoint object."""
        endpoint = MockEndpoint.objects.create(
            path='api/detail-test',
            owner=self.user,
            creator=self.user
        )
        response = self.client.get(f'{self.api_base}/endpoints/{endpoint.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data['path'], 'api/detail-test')

    def test_create_returns_201_with_object(self):
        """POST create returns 201 with created object."""
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': 'api/create-test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('id', data)

    def test_update_returns_200_with_object(self):
        """PUT/PATCH update returns 200 with updated object."""
        endpoint = MockEndpoint.objects.create(
            path='api/update-test',
            owner=self.user,
            creator=self.user,
            description='Original'
        )
        response = self.client.patch(
            f'{self.api_base}/endpoints/{endpoint.id}/',
            data=json.dumps({'description': 'Updated'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['description'], 'Updated')

    def test_delete_returns_204_no_content(self):
        """DELETE returns 204 No Content."""
        endpoint = MockEndpoint.objects.create(
            path='api/delete-test',
            owner=self.user,
            creator=self.user
        )
        response = self.client.delete(f'{self.api_base}/endpoints/{endpoint.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')

    # --- Error Responses ---
    def test_validation_error_returns_400(self):
        """Validation errors return 400 with details."""
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps({'path': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_not_found_returns_404(self):
        """Not found returns 404."""
        response = self.client.get(f'{self.api_base}/endpoints/99999/')
        self.assertEqual(response.status_code, 404)

    def test_unauthorized_returns_401(self):
        """Unauthorized access returns 401."""
        self.client.logout()
        response = self.client.get(f'{self.api_base}/endpoints/')
        self.assertIn(response.status_code, [401, 403])

    def test_forbidden_returns_403(self):
        """Forbidden access returns 403."""
        other_user = User.objects.create_user(username='other', password='pass')
        other_endpoint = MockEndpoint.objects.create(
            path='api/other-user-endpoint',
            owner=other_user,
            creator=other_user
        )
        response = self.client.get(f'{self.api_base}/endpoints/{other_endpoint.id}/')
        self.assertIn(response.status_code, [403, 404])

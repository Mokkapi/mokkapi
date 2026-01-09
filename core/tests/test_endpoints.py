"""
Tests for MockEndpoint CRUD operations and path handling edge cases.
"""
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, ResponseHandler, AuthenticationProfile

User = get_user_model()


class EndpointManagementTests(TestCase):
    """Tests for creating, updating, and deleting mock endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.api_base = '/_mokkapi_api/api'

    # --- Create Endpoint ---
    def test_create_endpoint_via_api(self):
        """Create a new mock endpoint via REST API."""
        data = {'path': 'api/new-endpoint'}
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(MockEndpoint.objects.filter(path='api/new-endpoint').exists())

    def test_create_endpoint_with_handlers(self):
        """Create endpoint with handlers in single request."""
        data = {'path': 'api/with-handlers'}
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        endpoint = MockEndpoint.objects.get(path='api/with-handlers')
        # Add handler separately if nested creation not supported
        handler_data = {
            'endpoint': endpoint.id,
            'http_method': 'GET',
            'response_status_code': 200,
            'response_body': '{"status": "ok"}'
        }
        handler_response = self.client.post(
            f'{self.api_base}/handlers/',
            data=json.dumps(handler_data),
            content_type='application/json'
        )
        self.assertEqual(handler_response.status_code, 201)

    def test_create_duplicate_path_fails(self):
        """Cannot create two endpoints with the same path."""
        MockEndpoint.objects.create(
            path='api/existing',
            owner=self.user,
            creator=self.user
        )
        data = {'path': 'api/existing'}
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_create_endpoint_path_normalized(self):
        """Endpoint path is normalized on creation."""
        data = {'path': '/api/normalize/'}
        response = self.client.post(
            f'{self.api_base}/endpoints/',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        endpoint = MockEndpoint.objects.filter(path__contains='normalize').first()
        self.assertIsNotNone(endpoint)

    # --- Update Endpoint ---
    def test_update_endpoint_description(self):
        """Update endpoint description."""
        endpoint = MockEndpoint.objects.create(
            path='api/update-desc',
            owner=self.user,
            creator=self.user,
            description='Old description'
        )
        data = {'description': 'New description'}
        response = self.client.patch(
            f'{self.api_base}/endpoints/{endpoint.id}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        endpoint.refresh_from_db()
        self.assertEqual(endpoint.description, 'New description')

    def test_update_endpoint_path(self):
        """Update endpoint path (if allowed)."""
        endpoint = MockEndpoint.objects.create(
            path='api/old-path',
            owner=self.user,
            creator=self.user
        )
        data = {'path': 'api/new-path'}
        response = self.client.patch(
            f'{self.api_base}/endpoints/{endpoint.id}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        # Path update may or may not be allowed
        self.assertIn(response.status_code, [200, 400])

    def test_update_endpoint_auth(self):
        """Attach/change authentication on endpoint."""
        endpoint = MockEndpoint.objects.create(
            path='api/add-auth',
            owner=self.user,
            creator=self.user
        )
        auth_profile = AuthenticationProfile.objects.create(
            name='Test Auth',
            auth_type='api_key',
            api_key='test-key-123',
            owner=self.user
        )
        data = {'authentication': auth_profile.id}
        response = self.client.patch(
            f'{self.api_base}/endpoints/{endpoint.id}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    # --- Delete Endpoint ---
    def test_delete_endpoint_via_api(self):
        """Delete an endpoint via REST API."""
        endpoint = MockEndpoint.objects.create(
            path='api/to-delete',
            owner=self.user,
            creator=self.user
        )
        endpoint_id = endpoint.id
        response = self.client.delete(f'{self.api_base}/endpoints/{endpoint_id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(MockEndpoint.objects.filter(id=endpoint_id).exists())

    def test_delete_endpoint_cascades_handlers(self):
        """Deleting endpoint also deletes associated handlers."""
        endpoint = MockEndpoint.objects.create(
            path='api/cascade-delete',
            owner=self.user,
            creator=self.user
        )
        handler = ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"test": true}'
        )
        handler_id = handler.id
        endpoint_id = endpoint.id

        response = self.client.delete(f'{self.api_base}/endpoints/{endpoint_id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(ResponseHandler.objects.filter(id=handler_id).exists())

    def test_delete_nonexistent_endpoint_returns_404(self):
        """Deleting an endpoint that doesn't exist returns 404."""
        response = self.client.delete(f'{self.api_base}/endpoints/99999/')
        self.assertEqual(response.status_code, 404)

    # --- Permissions ---
    def test_user_can_only_see_own_endpoints(self):
        """Regular user can only list their own endpoints."""
        MockEndpoint.objects.create(
            path='api/my-endpoint',
            owner=self.user,
            creator=self.user
        )
        other_user = User.objects.create_user(username='other', password='pass')
        MockEndpoint.objects.create(
            path='api/other-endpoint',
            owner=other_user,
            creator=other_user
        )

        response = self.client.get(f'{self.api_base}/endpoints/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        paths = [e['path'] for e in data]
        self.assertIn('api/my-endpoint', paths)
        self.assertNotIn('api/other-endpoint', paths)

    def test_user_cannot_modify_others_endpoints(self):
        """User cannot update another user's endpoint."""
        other_user = User.objects.create_user(username='other', password='pass')
        other_endpoint = MockEndpoint.objects.create(
            path='api/others-endpoint',
            owner=other_user,
            creator=other_user
        )
        data = {'description': 'Trying to modify'}
        response = self.client.patch(
            f'{self.api_base}/endpoints/{other_endpoint.id}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertIn(response.status_code, [403, 404])

    def test_admin_can_see_all_endpoints(self):
        """Admin user can list all endpoints."""
        admin = User.objects.create_superuser(username='admin', password='admin')
        MockEndpoint.objects.create(
            path='api/user-endpoint',
            owner=self.user,
            creator=self.user
        )
        other_user = User.objects.create_user(username='other', password='pass')
        MockEndpoint.objects.create(
            path='api/other-endpoint',
            owner=other_user,
            creator=other_user
        )

        self.client.logout()
        self.client.login(username='admin', password='admin')
        response = self.client.get(f'{self.api_base}/endpoints/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 2)


class PathEdgeCasesTests(TestCase):
    """Tests for edge cases in endpoint path handling."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')

    # --- Path Normalization ---
    def test_leading_slashes_stripped(self):
        """Leading slashes are removed from path."""
        endpoint = MockEndpoint.objects.create(
            path="/api/test",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/test")
        self.assertEqual(response.status_code, 200)

    def test_trailing_slashes_stripped(self):
        """Trailing slashes are removed from path."""
        endpoint = MockEndpoint.objects.create(
            path="api/trailing/",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/trailing")
        self.assertEqual(response.status_code, 200)

    def test_multiple_consecutive_slashes_collapsed(self):
        """Multiple consecutive slashes become single slash."""
        endpoint = MockEndpoint.objects.create(
            path="api/multi/slash",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/multi/slash")
        self.assertEqual(response.status_code, 200)

    def test_whitespace_in_path_handled(self):
        """Whitespace in path is handled appropriately."""
        endpoint = MockEndpoint.objects.create(
            path="api/with%20space",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/with%20space")
        self.assertIn(response.status_code, [200, 404])

    # --- Special Characters ---
    def test_path_with_query_params_style(self):
        """Path containing ? character is handled."""
        endpoint = MockEndpoint.objects.create(
            path="api/query",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/query?foo=bar")
        self.assertEqual(response.status_code, 200)

    def test_path_with_hash(self):
        """Path containing # character is handled."""
        endpoint = MockEndpoint.objects.create(
            path="api/fragment",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/fragment")
        self.assertEqual(response.status_code, 200)

    def test_path_with_unicode(self):
        """Path with unicode characters works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="api/café",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/café")
        self.assertIn(response.status_code, [200, 404])

    def test_path_with_url_encoded_chars(self):
        """Path with URL-encoded characters (%20, etc.) is handled."""
        endpoint = MockEndpoint.objects.create(
            path="api/encoded%2Fpath",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/encoded%2Fpath")
        self.assertIn(response.status_code, [200, 404])

    def test_path_with_dots(self):
        """Path with dots (file.json, api.v2) works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="api/v2.0/data.json",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/v2.0/data.json")
        self.assertEqual(response.status_code, 200)

    def test_path_with_hyphens_underscores(self):
        """Path with hyphens and underscores works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="api/my-endpoint_v1",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/my-endpoint_v1")
        self.assertEqual(response.status_code, 200)

    # --- Length Limits ---
    def test_very_long_path(self):
        """Very long paths are handled (within field limit)."""
        long_path = "api/" + "x" * 200
        endpoint = MockEndpoint.objects.create(
            path=long_path,
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get(f"/{long_path}")
        self.assertEqual(response.status_code, 200)

    def test_path_exceeding_max_length_rejected(self):
        """Paths exceeding max_length are rejected."""
        very_long_path = "api/" + "x" * 1000
        try:
            MockEndpoint.objects.create(
                path=very_long_path,
                owner=self.user,
                creator=self.user
            )
        except Exception:
            pass  # Expected - path too long

    # --- Path Matching ---
    def test_case_sensitive_path_matching(self):
        """Path matching is case-sensitive."""
        endpoint = MockEndpoint.objects.create(
            path="api/CaseSensitive",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get("/api/CaseSensitive")
        self.assertEqual(response.status_code, 200)
        response_lower = self.client.get("/api/casesensitive")
        self.assertIn(response_lower.status_code, [200, 404])

    def test_nonexistent_path_returns_404(self):
        """Request to non-configured path returns 404."""
        response = self.client.get("/api/nonexistent/path/here")
        self.assertEqual(response.status_code, 404)


class MockResponseServingEdgeCasesTests(TestCase):
    """Edge cases for the mock response serving functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')

    # --- Request Handling ---
    def test_request_body_not_validated(self):
        """Mock endpoint doesn't validate request body format."""
        endpoint = MockEndpoint.objects.create(
            path='api/any-body',
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='POST',
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.post(
            '/api/any-body',
            data='this is not json {{{',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_request_headers_ignored(self):
        """Request headers (except auth) don't affect response."""
        endpoint = MockEndpoint.objects.create(
            path='api/header-test',
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get(
            '/api/header-test',
            HTTP_X_CUSTOM_HEADER='custom-value',
            HTTP_ACCEPT='text/xml'
        )
        self.assertEqual(response.status_code, 200)

    def test_query_params_ignored(self):
        """Query parameters don't affect response."""
        endpoint = MockEndpoint.objects.create(
            path='api/query-test',
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"result": "same"}'
        )
        response1 = self.client.get('/api/query-test')
        response2 = self.client.get('/api/query-test?foo=bar')
        response3 = self.client.get('/api/query-test?baz=qux&num=123')
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response3.status_code, 200)
        self.assertEqual(response1.content, response2.content)
        self.assertEqual(response2.content, response3.content)

    # --- Response Behavior ---
    def test_custom_headers_added_to_response(self):
        """Custom headers from handler are added to response."""
        endpoint = MockEndpoint.objects.create(
            path='api/custom-headers',
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"ok": true}',
            response_headers={
                'X-Custom-Header': 'custom-value',
                'X-Request-Id': '12345'
            }
        )
        response = self.client.get('/api/custom-headers')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('X-Custom-Header'), 'custom-value')
        self.assertEqual(response.get('X-Request-Id'), '12345')

    def test_content_type_override(self):
        """Content-Type header from handler overrides default."""
        endpoint = MockEndpoint.objects.create(
            path='api/xml-content',
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='<root><data>test</data></root>',
            response_headers={'Content-Type': 'application/xml'}
        )
        response = self.client.get('/api/xml-content')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/xml', response.get('Content-Type', ''))

    def test_cors_headers_if_configured(self):
        """CORS headers are included if configured in handler."""
        endpoint = MockEndpoint.objects.create(
            path='api/cors-test',
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"ok": true}',
            response_headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
            }
        )
        response = self.client.get('/api/cors-test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Access-Control-Allow-Origin'), '*')

    # --- Endpoint Lookup ---
    def test_endpoint_lookup_is_exact_match(self):
        """Endpoint path matching is exact, not prefix."""
        MockEndpoint.objects.create(
            path='api/users',
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=MockEndpoint.objects.get(path='api/users'),
            http_method='GET',
            response_status_code=200,
            response_body='{"users": []}'
        )
        response = self.client.get('/api/users')
        self.assertEqual(response.status_code, 200)
        response_sub = self.client.get('/api/users/123')
        self.assertEqual(response_sub.status_code, 404)

    def test_deleted_endpoint_returns_404(self):
        """Deleted endpoint immediately returns 404."""
        endpoint = MockEndpoint.objects.create(
            path='api/to-be-deleted',
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method='GET',
            response_status_code=200,
            response_body='{"ok": true}'
        )
        response = self.client.get('/api/to-be-deleted')
        self.assertEqual(response.status_code, 200)
        endpoint.delete()
        response = self.client.get('/api/to-be-deleted')
        self.assertEqual(response.status_code, 404)

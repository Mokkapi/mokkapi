"""
Tests for ResponseHandler CRUD operations via the REST API.
"""
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, ResponseHandler

User = get_user_model()


class ResponseHandlerCRUDTests(TestCase):
    """Tests for creating, updating, and deleting response handlers."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.endpoint = MockEndpoint.objects.create(
            path="test/handlers",
            owner=self.user,
            creator=self.user
        )
        self.api_base = '/_mokkapi_api/api'

    # --- Create Handler ---
    def test_create_handler_via_api(self):
        """Create a new handler for an endpoint via REST API."""
        response = self.client.post(
            f"{self.api_base}/handlers/",
            data=json.dumps({
                "endpoint": self.endpoint.id,
                "http_method": "GET",
                "response_status_code": 200,
                "response_body": '{"test": true}'
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ResponseHandler.objects.filter(endpoint=self.endpoint, http_method="GET").exists())

    def test_create_handler_with_all_fields(self):
        """Create handler with status, headers, body, and description."""
        response = self.client.post(
            f"{self.api_base}/handlers/",
            data=json.dumps({
                "endpoint": self.endpoint.id,
                "http_method": "POST",
                "response_status_code": 201,
                "response_headers": {"Content-Type": "application/json", "X-Custom": "value"},
                "response_body": '{"created": true}',
                "description": "Creates a new resource"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        handler = ResponseHandler.objects.get(endpoint=self.endpoint, http_method="POST")
        self.assertEqual(handler.response_status_code, 201)
        self.assertEqual(handler.response_headers["X-Custom"], "value")
        self.assertEqual(handler.description, "Creates a new resource")

    def test_create_duplicate_method_handler_fails(self):
        """Cannot create two handlers with same HTTP method for one endpoint."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        response = self.client.post(
            f"{self.api_base}/handlers/",
            data=json.dumps({
                "endpoint": self.endpoint.id,
                "http_method": "GET",
                "response_status_code": 200,
                "response_body": '{}'
            }),
            content_type="application/json"
        )
        self.assertIn(response.status_code, [400, 409])

    def test_create_handler_normalizes_method_to_uppercase(self):
        """HTTP method is normalized to uppercase on creation."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="get",
            response_status_code=200,
            response_body='{}'
        )
        handler.refresh_from_db()
        self.assertEqual(handler.http_method, "GET")

    # --- Update Handler ---
    def test_update_handler_response_body(self):
        """Update an existing handler's response body."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"old": "body"}'
        )
        response = self.client.patch(
            f"{self.api_base}/handlers/{handler.id}/",
            data=json.dumps({"response_body": '{"new": "body"}'}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        handler.refresh_from_db()
        self.assertEqual(handler.response_body, '{"new": "body"}')

    def test_update_handler_status_code(self):
        """Update an existing handler's status code."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        response = self.client.patch(
            f"{self.api_base}/handlers/{handler.id}/",
            data=json.dumps({"response_status_code": 404}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        handler.refresh_from_db()
        self.assertEqual(handler.response_status_code, 404)

    def test_update_handler_headers(self):
        """Update an existing handler's response headers."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/plain"},
            response_body='{}'
        )
        new_headers = {"Content-Type": "application/json", "X-New": "header"}
        response = self.client.patch(
            f"{self.api_base}/handlers/{handler.id}/",
            data=json.dumps({"response_headers": new_headers}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        handler.refresh_from_db()
        self.assertEqual(handler.response_headers["X-New"], "header")

    def test_update_handler_method_not_allowed(self):
        """Cannot change a handler's HTTP method (must delete and recreate)."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        response = self.client.patch(
            f"{self.api_base}/handlers/{handler.id}/",
            data=json.dumps({"http_method": "POST"}),
            content_type="application/json"
        )
        handler.refresh_from_db()
        if response.status_code == 200:
            self.assertEqual(handler.http_method, "GET")

    # --- Delete Handler ---
    def test_delete_handler_via_api(self):
        """Delete an existing handler via REST API."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        handler_id = handler.id
        response = self.client.delete(f"{self.api_base}/handlers/{handler_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(ResponseHandler.objects.filter(id=handler_id).exists())

    def test_delete_handler_endpoint_still_exists(self):
        """Deleting a handler does not delete the parent endpoint."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        endpoint_id = self.endpoint.id
        self.client.delete(f"{self.api_base}/handlers/{handler.id}/")
        self.assertTrue(MockEndpoint.objects.filter(id=endpoint_id).exists())

    def test_delete_last_handler_endpoint_returns_405(self):
        """After deleting all handlers, endpoint returns 405 for all methods."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        self.client.delete(f"{self.api_base}/handlers/{handler.id}/")
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 405)

    def test_delete_nonexistent_handler_returns_404(self):
        """Deleting a handler that doesn't exist returns 404."""
        response = self.client.delete(f"{self.api_base}/handlers/99999/")
        self.assertEqual(response.status_code, 404)

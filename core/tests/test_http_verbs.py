"""
Tests for HTTP verb handling on mock endpoints.
"""
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, ResponseHandler

User = get_user_model()


class HTTPVerbTests(TestCase):
    """Tests for all HTTP verbs hitting mock endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.endpoint = MockEndpoint.objects.create(
            path="test/verbs",
            owner=self.user,
            creator=self.user
        )

    # --- GET ---
    def test_get_returns_configured_response(self):
        """GET request returns the configured response body and status."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"message": "success"}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "success"})

    def test_get_returns_configured_headers(self):
        """GET request returns configured custom headers."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"X-Custom-Header": "custom-value", "Content-Type": "application/json"},
            response_body='{}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response["X-Custom-Header"], "custom-value")

    def test_get_without_handler_returns_405(self):
        """GET request to endpoint without GET handler returns 405."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="POST",
            response_status_code=201,
            response_body='{}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 405)

    # --- POST ---
    def test_post_returns_configured_response(self):
        """POST request returns the configured response body and status."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="POST",
            response_status_code=201,
            response_body='{"created": true}'
        )
        response = self.client.post(f"/{self.endpoint.path}", content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"created": True})

    def test_post_ignores_request_body(self):
        """POST handler returns configured response regardless of request body."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="POST",
            response_status_code=201,
            response_body='{"static": "response"}'
        )
        response = self.client.post(
            f"/{self.endpoint.path}",
            data=json.dumps({"different": "data"}),
            content_type="application/json"
        )
        self.assertEqual(response.json(), {"static": "response"})

    def test_post_without_handler_returns_405(self):
        """POST request to endpoint without POST handler returns 405."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        response = self.client.post(f"/{self.endpoint.path}", content_type="application/json")
        self.assertEqual(response.status_code, 405)

    # --- PUT ---
    def test_put_returns_configured_response(self):
        """PUT request returns the configured response body and status."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="PUT",
            response_status_code=200,
            response_body='{"updated": true}'
        )
        response = self.client.put(f"/{self.endpoint.path}", content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"updated": True})

    def test_put_without_handler_returns_405(self):
        """PUT request to endpoint without PUT handler returns 405."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        response = self.client.put(f"/{self.endpoint.path}", content_type="application/json")
        self.assertEqual(response.status_code, 405)

    # --- PATCH ---
    def test_patch_returns_configured_response(self):
        """PATCH request returns the configured response body and status."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="PATCH",
            response_status_code=200,
            response_body='{"patched": true}'
        )
        response = self.client.patch(f"/{self.endpoint.path}", content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"patched": True})

    def test_patch_without_handler_returns_405(self):
        """PATCH request to endpoint without PATCH handler returns 405."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        response = self.client.patch(f"/{self.endpoint.path}", content_type="application/json")
        self.assertEqual(response.status_code, 405)

    # --- DELETE ---
    def test_delete_returns_configured_response(self):
        """DELETE request returns the configured response body and status."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="DELETE",
            response_status_code=200,
            response_body='{"deleted": true}'
        )
        response = self.client.delete(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"deleted": True})

    def test_delete_with_empty_body(self):
        """DELETE request can return empty body with appropriate status."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="DELETE",
            response_status_code=204,
            response_body=''
        )
        response = self.client.delete(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')

    def test_delete_without_handler_returns_405(self):
        """DELETE request to endpoint without DELETE handler returns 405."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        response = self.client.delete(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 405)

    # --- OPTIONS ---
    def test_options_returns_configured_response(self):
        """OPTIONS request returns the configured response."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="OPTIONS",
            response_status_code=200,
            response_headers={"Allow": "GET, POST, OPTIONS"},
            response_body=''
        )
        response = self.client.options(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)

    def test_options_without_handler_returns_405(self):
        """OPTIONS request to endpoint without OPTIONS handler returns 405."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        response = self.client.options(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 405)

    # --- HEAD ---
    def test_head_returns_headers_without_body(self):
        """HEAD request returns headers but no body."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="HEAD",
            response_status_code=200,
            response_headers={"X-Custom": "value"},
            response_body='This should not appear'
        )
        response = self.client.head(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_head_without_handler_returns_405(self):
        """HEAD request to endpoint without HEAD handler returns 405."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        response = self.client.head(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 405)

    # --- Multiple Handlers ---
    def test_endpoint_with_multiple_handlers(self):
        """Endpoint with GET and POST handlers routes correctly."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"method": "GET"}'
        )
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="POST",
            response_status_code=201,
            response_body='{"method": "POST"}'
        )

        get_response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json(), {"method": "GET"})

        post_response = self.client.post(f"/{self.endpoint.path}", content_type="application/json")
        self.assertEqual(post_response.status_code, 201)
        self.assertEqual(post_response.json(), {"method": "POST"})

    def test_405_includes_allow_header(self):
        """405 response includes Allow header listing available methods."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{}'
        )
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="POST",
            response_status_code=201,
            response_body='{}'
        )
        response = self.client.put(f"/{self.endpoint.path}", content_type="application/json")
        self.assertEqual(response.status_code, 405)
        self.assertIn("Allow", response)
        allow_header = response["Allow"]
        self.assertIn("GET", allow_header)
        self.assertIn("POST", allow_header)

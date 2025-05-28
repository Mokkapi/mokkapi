from django.core.exceptions import ValidationError
from django.test import TestCase, Client

import json
import unittest

from .models import MokkBaseJSON


class MokkBaseJSONModelTests(TestCase):
    def test_path_normalization(self):
        """Ensure the clean() method normalizes paths correctly."""
        endpoint = MokkBaseJSON(
            name="Test Endpoint",
            path="/some//unique//path/",
            data={"key": "value"}
        )
        endpoint.clean()  # This should normalize the path
        self.assertEqual(endpoint.path, "some/unique/path")

    def test_path_empty_after_normalization(self):
        """Ensure that a path that normalizes to empty raises a ValidationError."""
        endpoint = MokkBaseJSON(
            name="Test Empty",
            path="///",
            data={"key": "value"}
        )
        with self.assertRaises(ValidationError):
            endpoint.clean()

    def test_str_method(self):
        """Test that the __str__ method returns the normalized path with a leading slash."""
        endpoint = MokkBaseJSON(
            name="Test Str",
            path="some/unique/path",
            data={"key": "value"}
        )
        self.assertEqual(str(endpoint), "/some/unique/path")


class APIEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a mock endpoint with JSON data.
        self.endpoint = MokkBaseJSON.objects.create(
            name="JSON Endpoint",
            path="some/unique/path",
            data={"key": "value"}
        )

    def test_get_json_response(self):
        """Test that a GET request to the endpoint returns the JSON data."""
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.endpoint.data)

    @unittest.skip("POST endpoint functionality not implemented yet")
    def test_post_json_endpoint(self):
        """Test that a POST request will handle JSON input and update/create data.
           This test is pending until the POST functionality is built."""
        payload = {"new_key": "new_value"}
        response = self.client.post(
            f"/{self.endpoint.path}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        # Further assertions could verify that the endpoint data was updated or a new record created

    @unittest.skip("XML response functionality not implemented yet")
    def test_get_xml_response(self):
        """Test that a GET request with Accept header 'application/xml' returns XML data.
           This is a placeholder until XML rendering is implemented."""
        # For demonstration, assume we store XML data directly.
        self.endpoint.data = "<response>value</response>"
        self.endpoint.save()
        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_ACCEPT="application/xml"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("xml", response["Content-Type"])
        self.assertEqual(response.content.decode(), self.endpoint.data)

    @unittest.skip("API key authentication not implemented yet")
    def test_api_key_authentication(self):
        """Test that the endpoint requires an API key for access.
           Assumes a future 'api_key' field and validation."""
        # Hypothetical: set an API key on the endpoint
        self.endpoint.api_key = "ABC123"
        self.endpoint.save()
        # Request with correct key
        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY="ABC123"
        )
        self.assertEqual(response.status_code, 200)
        # Request with wrong key
        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_X_API_KEY="WRONG"
        )
        self.assertEqual(response.status_code, 401)

    @unittest.skip("Username/password authentication not implemented yet")
    def test_basic_authentication(self):
        """Test that basic authentication (username/password) works as expected.
           This is a stub for future implementation."""
        # Hypothetical: mark the endpoint as requiring basic auth
        self.endpoint.requires_auth = True  # Future field
        self.endpoint.username = "user"
        self.endpoint.password = "pass"
        self.endpoint.save()
        # Test with correct credentials (base64 encoded "user:pass")
        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_AUTHORIZATION='Basic dXNlcjpwYXNz'
        )
        self.assertEqual(response.status_code, 200)
        # Test with incorrect credentials
        response = self.client.get(
            f"/{self.endpoint.path}",
            HTTP_AUTHORIZATION='Basic d3Jvbmc6Y3JlZHM='
        )
        self.assertEqual(response.status_code, 401)

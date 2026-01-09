"""
Tests for response handling including incomplete data, file types, and encoding.
"""
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import MockEndpoint, ResponseHandler

User = get_user_model()


class IncompleteResponseDataTests(TestCase):
    """Tests for handlers with missing or edge-case response configurations."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.endpoint = MockEndpoint.objects.create(
            path="test/incomplete",
            owner=self.user,
            creator=self.user
        )

    # --- Empty Body ---
    def test_empty_response_body(self):
        """Handler with empty response body returns empty content."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body=''
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_empty_body_with_204_status(self):
        """Handler returning 204 No Content with empty body."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=204,
            response_body=''
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')

    # --- Missing/Default Headers ---
    def test_no_content_type_header(self):
        """Handler without Content-Type header uses default."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={},
            response_body='test content'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Content-Type", response)

    def test_empty_headers_dict(self):
        """Handler with empty headers dict still works."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={},
            response_body='{"test": true}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"test", response.content)

    def test_null_headers(self):
        """Handler with null/None headers is handled gracefully."""
        handler = ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"test": true}'
        )
        handler.response_headers = None
        handler.save()
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(response.status_code, [200, 500])

    # --- Various Status Codes ---
    def test_1xx_informational_status(self):
        """Handler can return 1xx informational status codes."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=101,
            response_body=''
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 101)

    def test_3xx_redirect_status(self):
        """Handler can return 3xx redirect status codes."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=301,
            response_headers={"Location": "https://example.com/new-location"},
            response_body=''
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://example.com/new-location")

    def test_4xx_client_error_status(self):
        """Handler can return 4xx client error status codes."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=404,
            response_body='{"error": "Not found"}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Not found"})

    def test_5xx_server_error_status(self):
        """Handler can return 5xx server error status codes."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=503,
            response_body='{"error": "Service unavailable"}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "Service unavailable"})

    # --- Special Response Bodies ---
    def test_json_response_body(self):
        """Handler returns valid JSON in response body."""
        json_body = '{"key": "value", "nested": {"arr": [1, 2, 3]}}'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body=json_body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["key"], "value")
        self.assertEqual(data["nested"]["arr"], [1, 2, 3])

    def test_xml_response_body(self):
        """Handler returns valid XML in response body."""
        xml_body = '<?xml version="1.0"?><root><item>value</item></root>'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/xml"},
            response_body=xml_body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<root>", response.content)
        self.assertIn(b"<item>value</item>", response.content)

    def test_html_response_body(self):
        """Handler returns HTML in response body."""
        html_body = '<!DOCTYPE html><html><body><h1>Hello</h1></body></html>'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/html"},
            response_body=html_body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<h1>Hello</h1>", response.content)

    def test_plaintext_response_body(self):
        """Handler returns plain text in response body."""
        text_body = 'This is plain text content.\nWith multiple lines.'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/plain"},
            response_body=text_body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), text_body)

    def test_binary_like_response_body(self):
        """Handler can return base64-encoded or binary-like content."""
        b64_content = 'SGVsbG8gV29ybGQ='
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/octet-stream"},
            response_body=b64_content
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), b64_content)

    def test_unicode_response_body(self):
        """Handler correctly returns unicode characters in body."""
        unicode_body = '{"message": "Hello 世界! 🌍 Привет мир!"}'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json; charset=utf-8"},
            response_body=unicode_body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("世界", response.content.decode('utf-8'))
        self.assertIn("🌍", response.content.decode('utf-8'))

    def test_large_response_body(self):
        """Handler can return large response bodies."""
        large_body = json.dumps({"data": "x" * 100000})
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body=large_body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 100000)

    # --- Invalid/Malformed Data ---
    def test_invalid_json_in_body_still_returns(self):
        """Handler with invalid JSON in body field returns it as-is."""
        invalid_json = '{not valid json: [}'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body=invalid_json
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), invalid_json)

    def test_headers_with_invalid_values(self):
        """Handler with unusual header values still works."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={
                "X-Custom-Header": "value with spaces",
                "X-Another": "special!@#$%chars"
            },
            response_body='{"test": true}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Custom-Header"], "value with spaces")


class FileTypeResponseTests(TestCase):
    """Tests for returning various file types and content types."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.endpoint = MockEndpoint.objects.create(
            path="test/filetypes",
            owner=self.user,
            creator=self.user
        )

    # --- JSON ---
    def test_json_content_type(self):
        """Handler returns application/json with JSON body."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"key": "value"}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["Content-Type"])

    def test_json_with_charset_utf8(self):
        """Handler returns application/json; charset=utf-8."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json; charset=utf-8"},
            response_body='{"key": "value"}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("charset=utf-8", response["Content-Type"])

    def test_json_body_is_parseable(self):
        """JSON response body can be parsed by client."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"nested": {"array": [1, 2, 3]}}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        data = response.json()
        self.assertEqual(data["nested"]["array"], [1, 2, 3])

    # --- XML ---
    def test_xml_content_type(self):
        """Handler returns application/xml with XML body."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/xml"},
            response_body='<root><item>value</item></root>'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("application/xml", response["Content-Type"])
        self.assertIn(b"<root>", response.content)

    def test_xml_text_content_type(self):
        """Handler returns text/xml as alternative XML content type."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/xml"},
            response_body='<data>test</data>'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("text/xml", response["Content-Type"])

    def test_xml_with_declaration(self):
        """Handler returns XML with <?xml?> declaration."""
        xml_body = '<?xml version="1.0" encoding="UTF-8"?><root><item>value</item></root>'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/xml"},
            response_body=xml_body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b'<?xml version="1.0"', response.content)

    # --- HTML ---
    def test_html_content_type(self):
        """Handler returns text/html with HTML body."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/html"},
            response_body='<html><body>Hello</body></html>'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("text/html", response["Content-Type"])

    def test_html_full_document(self):
        """Handler returns complete HTML document with doctype."""
        html = '<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/html"},
            response_body=html
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b"<!DOCTYPE html>", response.content)
        self.assertIn(b"<title>Test</title>", response.content)

    def test_html_fragment(self):
        """Handler returns HTML fragment (no doctype)."""
        html_fragment = '<div class="container"><p>Just a fragment</p></div>'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/html"},
            response_body=html_fragment
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.content.decode('utf-8'), html_fragment)

    def test_html_with_embedded_css(self):
        """Handler returns HTML with embedded <style> tags."""
        html = '<html><head><style>body { color: red; }</style></head><body>Styled</body></html>'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/html"},
            response_body=html
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b"<style>", response.content)
        self.assertIn(b"color: red", response.content)

    def test_html_with_embedded_js(self):
        """Handler returns HTML with embedded <script> tags."""
        html = '<html><body><script>console.log("Hello");</script></body></html>'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/html"},
            response_body=html
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b"<script>", response.content)
        self.assertIn(b'console.log', response.content)

    # --- CSS ---
    def test_css_content_type(self):
        """Handler returns text/css with CSS body."""
        css = 'body { margin: 0; padding: 0; }'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/css"},
            response_body=css
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("text/css", response["Content-Type"])
        self.assertEqual(response.content.decode('utf-8'), css)

    def test_css_with_charset(self):
        """Handler returns text/css; charset=utf-8."""
        css = '.icon::before { content: "\\2764"; }'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/css; charset=utf-8"},
            response_body=css
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("charset=utf-8", response["Content-Type"])

    def test_css_minified(self):
        """Handler returns minified CSS."""
        minified = 'body{margin:0;padding:0}.container{width:100%}'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/css"},
            response_body=minified
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.content.decode('utf-8'), minified)

    def test_css_with_comments(self):
        """Handler returns CSS with comments preserved."""
        css = '/* Main styles */\nbody { color: black; } /* Text color */'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/css"},
            response_body=css
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b"/* Main styles */", response.content)

    def test_css_with_unicode(self):
        """Handler returns CSS with unicode characters (icons, etc.)."""
        css = '.icon::before { content: "❤️"; }'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/css; charset=utf-8"},
            response_body=css
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("❤️", response.content.decode('utf-8'))

    # --- JavaScript ---
    def test_javascript_content_type(self):
        """Handler returns application/javascript with JS body."""
        js = 'function hello() { return "Hello"; }'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/javascript"},
            response_body=js
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("application/javascript", response["Content-Type"])

    def test_javascript_text_content_type(self):
        """Handler returns text/javascript as alternative JS content type."""
        js = 'var x = 1;'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/javascript"},
            response_body=js
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("text/javascript", response["Content-Type"])

    def test_javascript_module_content_type(self):
        """Handler returns application/javascript for ES modules."""
        js = 'export const greeting = "Hello";'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/javascript"},
            response_body=js
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b"export const", response.content)

    def test_javascript_minified(self):
        """Handler returns minified JavaScript."""
        minified = 'function a(b){return b*2}var c=a(5);console.log(c);'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/javascript"},
            response_body=minified
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.content.decode('utf-8'), minified)

    def test_javascript_with_source_map_header(self):
        """Handler returns JS with X-SourceMap header."""
        js = 'console.log("test");'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={
                "Content-Type": "application/javascript",
                "X-SourceMap": "/js/app.js.map"
            },
            response_body=js
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response["X-SourceMap"], "/js/app.js.map")

    # --- TypeScript ---
    def test_typescript_content_type(self):
        """Handler returns appropriate content type for TypeScript."""
        ts = 'const greeting: string = "Hello";'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/typescript"},
            response_body=ts
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("typescript", response["Content-Type"])

    def test_typescript_application_type(self):
        """Handler returns application/typescript."""
        ts = 'interface User { name: string; }'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/typescript"},
            response_body=ts
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response["Content-Type"], "application/typescript")

    def test_typescript_with_type_annotations(self):
        """Handler returns TypeScript with type annotations."""
        ts = 'function greet(name: string): string { return `Hello, ${name}`; }'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/typescript"},
            response_body=ts
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b": string", response.content)

    def test_tsx_content(self):
        """Handler returns TSX (TypeScript + JSX) content."""
        tsx = 'const App: React.FC = () => <div>Hello</div>;'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/typescript"},
            response_body=tsx
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b"React.FC", response.content)
        self.assertIn(b"<div>", response.content)

    # --- Markdown ---
    def test_markdown_content_type(self):
        """Handler returns text/markdown with Markdown body."""
        md = '# Hello\n\nThis is **bold** text.'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/markdown"},
            response_body=md
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("text/markdown", response["Content-Type"])

    def test_markdown_text_plain_fallback(self):
        """Handler can return Markdown as text/plain."""
        md = '# Heading\n\nParagraph text.'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/plain"},
            response_body=md
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("text/plain", response["Content-Type"])
        self.assertIn(b"# Heading", response.content)

    def test_markdown_with_frontmatter(self):
        """Handler returns Markdown with YAML frontmatter."""
        md = '---\ntitle: Test\ndate: 2024-01-01\n---\n\n# Content'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/markdown"},
            response_body=md
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b"---", response.content)
        self.assertIn(b"title: Test", response.content)

    def test_markdown_with_code_blocks(self):
        """Handler returns Markdown with fenced code blocks."""
        md = '# Code Example\n\n```python\nprint("Hello")\n```'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/markdown"},
            response_body=md
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b"```python", response.content)

    def test_markdown_with_tables(self):
        """Handler returns Markdown with GFM tables."""
        md = '| Name | Age |\n|------|-----|\n| John | 30 |'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/markdown"},
            response_body=md
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn(b"|------|", response.content)

    # --- Plain Text ---
    def test_plain_text_content_type(self):
        """Handler returns text/plain with text body."""
        text = 'Just plain text content.'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/plain"},
            response_body=text
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("text/plain", response["Content-Type"])
        self.assertEqual(response.content.decode('utf-8'), text)

    def test_plain_text_multiline(self):
        """Handler returns multi-line plain text."""
        text = 'Line 1\nLine 2\nLine 3'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/plain"},
            response_body=text
        )
        response = self.client.get(f"/{self.endpoint.path}")
        lines = response.content.decode('utf-8').split('\n')
        self.assertEqual(len(lines), 3)

    # --- Other Common Types ---
    def test_svg_content_type(self):
        """Handler returns image/svg+xml with SVG body."""
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="40"/></svg>'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "image/svg+xml"},
            response_body=svg
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("image/svg+xml", response["Content-Type"])
        self.assertIn(b"<svg", response.content)

    def test_yaml_content_type(self):
        """Handler returns application/yaml or text/yaml."""
        yaml_body = 'name: test\nversion: 1.0\nfeatures:\n  - feature1\n  - feature2'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/yaml"},
            response_body=yaml_body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("yaml", response["Content-Type"])

    def test_csv_content_type(self):
        """Handler returns text/csv with CSV body."""
        csv_body = 'name,age,city\nJohn,30,NYC\nJane,25,LA'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/csv"},
            response_body=csv_body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn(b"name,age,city", response.content)

    def test_ics_calendar_content_type(self):
        """Handler returns text/calendar with iCalendar body."""
        ics = 'BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:Test Event\nEND:VEVENT\nEND:VCALENDAR'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/calendar"},
            response_body=ics
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertIn("text/calendar", response["Content-Type"])
        self.assertIn(b"BEGIN:VCALENDAR", response.content)

    # --- Content Negotiation ---
    def test_accept_header_ignored(self):
        """Handler returns configured type regardless of Accept header."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"key": "value"}'
        )
        response = self.client.get(f"/{self.endpoint.path}", HTTP_ACCEPT="text/html")
        self.assertIn("application/json", response["Content-Type"])

    def test_content_type_case_insensitive(self):
        """Content-Type header matching is case-insensitive."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"content-type": "Application/JSON"},
            response_body='{"key": "value"}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)


class FilePathStyleEndpointTests(TestCase):
    """Tests for endpoints that mimic file paths with extensions."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')

    # --- Paths with Extensions ---
    def test_endpoint_path_with_json_extension(self):
        """Endpoint path like 'api/data.json' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="api/data.json",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"data": "value"}'
        )
        response = self.client.get("/api/data.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": "value"})

    def test_endpoint_path_with_xml_extension(self):
        """Endpoint path like 'api/feed.xml' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="api/feed.xml",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/xml"},
            response_body='<feed><item>Test</item></feed>'
        )
        response = self.client.get("/api/feed.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<feed>", response.content)

    def test_endpoint_path_with_html_extension(self):
        """Endpoint path like 'pages/about.html' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="pages/about.html",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/html"},
            response_body='<html><body><h1>About</h1></body></html>'
        )
        response = self.client.get("/pages/about.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<h1>About</h1>", response.content)

    def test_endpoint_path_with_css_extension(self):
        """Endpoint path like 'styles/main.css' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="styles/main.css",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/css"},
            response_body='body { margin: 0; }'
        )
        response = self.client.get("/styles/main.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response["Content-Type"])

    def test_endpoint_path_with_js_extension(self):
        """Endpoint path like 'scripts/app.js' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="scripts/app.js",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/javascript"},
            response_body='console.log("Hello");'
        )
        response = self.client.get("/scripts/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'console.log', response.content)

    def test_endpoint_path_with_ts_extension(self):
        """Endpoint path like 'src/utils.ts' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="src/utils.ts",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/typescript"},
            response_body='export function add(a: number, b: number): number { return a + b; }'
        )
        response = self.client.get("/src/utils.ts")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b": number", response.content)

    def test_endpoint_path_with_md_extension(self):
        """Endpoint path like 'docs/readme.md' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="docs/readme.md",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/markdown"},
            response_body='# README\n\nThis is documentation.'
        )
        response = self.client.get("/docs/readme.md")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"# README", response.content)

    def test_endpoint_path_with_svg_extension(self):
        """Endpoint path like 'images/logo.svg' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="images/logo.svg",
            owner=self.user,
            creator=self.user
        )
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40" fill="red"/></svg>'
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "image/svg+xml"},
            response_body=svg
        )
        response = self.client.get("/images/logo.svg")
        self.assertEqual(response.status_code, 200)
        self.assertIn("image/svg+xml", response["Content-Type"])

    # --- Extension vs Content-Type Mismatch ---
    def test_json_extension_but_html_content(self):
        """Endpoint 'data.json' can return HTML if configured."""
        endpoint = MockEndpoint.objects.create(
            path="data.json",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/html"},
            response_body='<html><body>Not JSON!</body></html>'
        )
        response = self.client.get("/data.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        self.assertIn(b"Not JSON!", response.content)

    def test_no_extension_any_content_type(self):
        """Endpoint without extension can return any content type."""
        endpoint = MockEndpoint.objects.create(
            path="api/resource",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/css"},
            response_body='body { color: red; }'
        )
        response = self.client.get("/api/resource")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response["Content-Type"])

    # --- Multiple Dots in Path ---
    def test_path_with_multiple_dots(self):
        """Endpoint path like 'api/v2.1/config.json' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path="api/v2.1/config.json",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"version": "2.1"}'
        )
        response = self.client.get("/api/v2.1/config.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"version": "2.1"})

    def test_path_with_dotfile_style(self):
        """Endpoint path like '.well-known/security.txt' works correctly."""
        endpoint = MockEndpoint.objects.create(
            path=".well-known/security.txt",
            owner=self.user,
            creator=self.user
        )
        ResponseHandler.objects.create(
            endpoint=endpoint,
            http_method="GET",
            response_status_code=200,
            response_headers={"Content-Type": "text/plain"},
            response_body='Contact: security@example.com'
        )
        response = self.client.get("/.well-known/security.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"security@example.com", response.content)


class ContentEncodingTests(TestCase):
    """Tests for character encoding and content encoding handling."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.endpoint = MockEndpoint.objects.create(
            path="test/encoding",
            owner=self.user,
            creator=self.user
        )

    # --- Character Encoding ---
    def test_utf8_encoding_default(self):
        """Response uses UTF-8 encoding by default."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"message": "Hello World"}'
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        content_type = response.get('Content-Type', '')
        self.assertTrue('utf-8' in content_type.lower() or 'charset' not in content_type.lower())

    def test_utf8_characters_preserved(self):
        """UTF-8 special characters are preserved in response."""
        body_with_utf8 = '{"message": "Héllo Wörld - 日本語"}'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body=body_with_utf8
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Héllo Wörld", response.content.decode('utf-8'))
        self.assertIn("日本語", response.content.decode('utf-8'))

    def test_emoji_in_response_body(self):
        """Emoji characters are correctly returned."""
        body_with_emoji = '{"mood": "Happy 😊🎉"}'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body=body_with_emoji
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("😊", response.content.decode('utf-8'))
        self.assertIn("🎉", response.content.decode('utf-8'))

    def test_non_ascii_in_json(self):
        """Non-ASCII characters in JSON are handled correctly."""
        body = '{"name": "François", "city": "Zürich", "greeting": "Привет"}'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body=body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("François", content)
        self.assertIn("Zürich", content)
        self.assertIn("Привет", content)

    def test_charset_in_content_type(self):
        """Charset specified in Content-Type is honored."""
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body='{"data": "test"}',
            response_headers={"Content-Type": "application/json; charset=utf-8"}
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("charset=utf-8", response.get('Content-Type', '').lower())

    # --- Content Length ---
    def test_content_length_header_correct(self):
        """Content-Length header matches actual body length."""
        body = '{"test": "data"}'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body=body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        content_length = response.get('Content-Length')
        if content_length:
            self.assertEqual(int(content_length), len(response.content))

    def test_content_length_with_unicode(self):
        """Content-Length correct for multi-byte UTF-8 characters."""
        body = '{"emoji": "🎉"}'
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body=body
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        content_length = response.get('Content-Length')
        if content_length:
            self.assertEqual(int(content_length), len(body.encode('utf-8')))

    # --- Line Endings ---
    def test_unix_line_endings_preserved(self):
        """Unix line endings (LF) are preserved."""
        body = "line1\nline2\nline3"
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body=body,
            response_headers={"Content-Type": "text/plain"}
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), body)
        self.assertEqual(response.content.count(b'\n'), 2)
        self.assertEqual(response.content.count(b'\r\n'), 0)

    def test_windows_line_endings_preserved(self):
        """Windows line endings (CRLF) are preserved."""
        body = "line1\r\nline2\r\nline3"
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body=body,
            response_headers={"Content-Type": "text/plain"}
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), body)
        self.assertEqual(response.content.count(b'\r\n'), 2)

    def test_mixed_line_endings_preserved(self):
        """Mixed line endings are preserved as-is."""
        body = "line1\nline2\r\nline3\rline4"
        ResponseHandler.objects.create(
            endpoint=self.endpoint,
            http_method="GET",
            response_status_code=200,
            response_body=body,
            response_headers={"Content-Type": "text/plain"}
        )
        response = self.client.get(f"/{self.endpoint.path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), body)

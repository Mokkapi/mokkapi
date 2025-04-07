import json
import base64
from behave import given, when, then
from django.test import Client
from .models import MokkBaseJSON

@given('a mock endpoint exists at path "{path}" with JSON data \'{json_data}\'')
def step_impl_create_json_endpoint(context, path, json_data):
    data = json.loads(json_data)
    context.endpoint = MokkBaseJSON.objects.create(path=path, data=data)

@given('a mock endpoint exists at path "{path}" with XML data "{xml_data}"')
def step_impl_create_xml_endpoint(context, path, xml_data):
    # In the future you might have a separate field or logic for XML data.
    # For now, we store XML as plain text in the JSONField.
    context.endpoint = MokkBaseJSON.objects.create(path=path, data=xml_data)

@given('a mock endpoint exists at path "{path}" that requires API key "{api_key}"')
def step_impl_create_api_key_endpoint(context, path, api_key):
    context.endpoint = MokkBaseJSON.objects.create(path=path, data={"message": "secured"})
    context.endpoint.api_key = api_key  # Hypothetical future field
    context.endpoint.save()

@given('a mock endpoint exists at path "{path}" that requires username "{username}" and password "{password}"')
def step_impl_create_basic_auth_endpoint(context, path, username, password):
    context.endpoint = MokkBaseJSON.objects.create(path=path, data={"message": "basic auth"})
    context.endpoint.requires_auth = True  # Hypothetical future field
    context.endpoint.username = username
    context.endpoint.password = password
    context.endpoint.save()

@when('I send a GET request to "{url}"')
def step_impl_get_request(context, url):
    context.client = Client()
    context.response = context.client.get(url)

@when('I send a GET request to "{url}" with header "Accept: {accept}"')
def step_impl_get_request_with_header(context, url, accept):
    context.client = Client()
    context.response = context.client.get(url, HTTP_ACCEPT=accept)

@when('I send a GET request to "{url}" with header "X-API-KEY: {api_key}"')
def step_impl_get_request_with_api_key(context, url, api_key):
    context.client = Client()
    context.response = context.client.get(url, HTTP_X_API_KEY=api_key)

@when('I send a GET request to "{url}" with Basic auth credentials "{creds}"')
def step_impl_get_request_with_basic_auth(context, url, creds):
    context.client = Client()
    token = base64.b64encode(creds.encode()).decode()
    context.response = context.client.get(url, HTTP_AUTHORIZATION=f'Basic {token}')

@when('I send a POST request to "{url}" with the payload')
def step_impl_post_request(context, url):
    context.client = Client()
    payload = json.loads(context.text)
    context.response = context.client.post(
        url, data=json.dumps(payload), content_type="application/json"
    )

@then('I receive a {status_code:d} response')
def step_impl_then_status_code(context, status_code):
    assert context.response.status_code == status_code

@then('I receive a {status_code:d} response with JSON data \'{json_data}\'')
def step_impl_then_json_response(context, status_code, json_data):
    assert context.response.status_code == status_code
    expected_data = json.loads(json_data)
    response_data = context.response.json()
    assert response_data == expected_data

@then('I receive a {status_code:d} response with XML data "{xml_data}"')
def step_impl_then_xml_response(context, status_code, xml_data):
    assert context.response.status_code == status_code
    # Verify that the XML data is part of the response.
    assert xml_data in context.response.content.decode()

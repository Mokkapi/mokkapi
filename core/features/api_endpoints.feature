Feature: Mock API Endpoints
  In order to test my application
  As a developer
  I want to create mock API endpoints with various response types and authentication options

  Scenario: GET request returns JSON response
    Given a mock endpoint exists at path "some/unique/path" with JSON data '{"key": "value"}'
    When I send a GET request to "/some/unique/path"
    Then I receive a 200 response with JSON data '{"key": "value"}'

  Scenario: GET request returns XML response when requested
    Given a mock endpoint exists at path "xml/endpoint" with XML data "<response>value</response>"
    When I send a GET request to "/xml/endpoint" with header "Accept: application/xml"
    Then I receive a 200 response with XML data "<response>value</response>"

  Scenario: POST request to create/update endpoint data
    Given I have a valid JSON payload '{"new_key": "new_value"}'
    When I send a POST request to "/some/unique/path" with the payload
    Then I receive a 201 response and the endpoint data is updated accordingly

  Scenario: API key authentication for accessing endpoint
    Given a mock endpoint exists at path "secured/endpoint" that requires API key "ABC123"
    When I send a GET request to "/secured/endpoint" with header "X-API-KEY: ABC123"
    Then I receive a 200 response

  Scenario: Basic authentication for accessing endpoint
    Given a mock endpoint exists at path "basic-auth/endpoint" that requires username "user" and password "pass"
    When I send a GET request to "/basic-auth/endpoint" with Basic auth credentials "user:pass"
    Then I receive a 200 response

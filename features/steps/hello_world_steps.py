import json

from behave import then, when
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ruff: noqa: F811 # Ignore redefinition of step_impl


@when('I send a GET request to "{path}"')
def step_impl(context, path):
    """Send a GET request to the specified path."""
    context.response = client.get(path)


@then("the response status code should be {status_code:d}")
def step_impl(context, status_code):
    """Check if the response status code matches the expected code."""
    assert context.response.status_code == status_code


@then("the response body should be JSON")
def step_impl(context):
    """Check if the response body is valid JSON."""
    try:
        context.response.json()
    except json.JSONDecodeError as e:
        raise AssertionError("Response body is not valid JSON") from e


@then("the response JSON should be {json_data}")
def step_impl(context, json_data):
    """Check if the response JSON matches the expected JSON data."""
    expected_json = json.loads(json_data)
    assert context.response.json() == expected_json

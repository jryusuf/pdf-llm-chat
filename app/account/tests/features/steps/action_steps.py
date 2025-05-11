from behave import when
from fastapi.testclient import TestClient


@when("the user attempts to register")
def step_impl(context):
    """
    Sends a registration request to the application endpoint.
    Assumes user data is stored in context.user_data by a Given step.
    """
    # Use the test client to make the POST request with the full placeholder URL
    context.response = context.client.post("http://testserver/account/register", json=context.user_data)


@when("the user attempts to log in")
def step_impl(context):
    """
    Sends a login request to the application endpoint.
    Assumes login data is stored in context.login_data by a Given step.
    """
    # Use the test client to make the POST request with the full placeholder URL
    context.response = context.client.post("http://testserver/account/login", json=context.login_data)

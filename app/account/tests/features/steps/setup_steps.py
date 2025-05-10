import asyncio
from behave import given
from sqlalchemy.ext.asyncio import AsyncSession
from app.account.infrastructure.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.account.domain.models import User as UserDomainModel
# Removed import of get_db_session as it's no longer called directly


@given("the user provides a valid email and a password meeting basic criteria")
def step_impl(context):
    """
    Prepares valid user registration data.
    """
    context.user_data = {"email": "test@example.com", "password": "Password123!"}


@given("a user with the email already exists")
def step_impl(context):
    """
    Registers a user before the scenario runs to simulate an existing user.
    Requires actual registration logic or database setup.
    """
    existing_email = "existing@example.com"
    existing_password = "Password123!"
    # Use the helper function from environment.py and the session from context
    context.loop.run_until_complete(
        context.add_user_via_repo(context.session, existing_email, existing_password)
    )
    context.existing_email = existing_email


@given("the user attempts to register with the existing email")
def step_impl(context):
    """
    Prepares user registration data using the existing email.
    """
    context.user_data = {"email": context.existing_email, "password": "NewPassword456!"}


@given("the user provides an invalid email format or a password not meeting basic requirements")
def step_impl(context):
    """
    Prepares invalid user registration data.
    """
    # Example invalid data
    context.user_data = {"email": "invalid-email", "password": "short"}


@given("a user account is registered")
def step_impl(context):
    """
    Registers a user account for login scenarios.
    Requires actual registration logic or database setup.
    """
    registered_email = "registered@example.com"
    registered_password = "Password123!"
    context.loop.run_until_complete(
        context.add_user_via_repo(context.session, registered_email, registered_password)
    )
    context.registered_user_email = registered_email
    context.registered_user_password = registered_password


@given("the user provides a valid registered email and correct password")
def step_impl(context):
    """
    Prepares valid user login data for a registered user.
    """
    context.login_data = {
        "email": context.registered_user_email,
        "password": context.registered_user_password,
    }


@given("the user provides a valid registered email but incorrect password")
def step_impl(context):
    """
    Prepares user login data with an incorrect password for a registered user.
    """
    context.login_data = {
        "email": context.registered_user_email,
        "password": "WrongPassword!",
    }


@given("the user attempts to log in with an email not registered in the system")
def step_impl(context):
    """
    Prepares user login data for a non-existent email.
    """
    context.login_data = {
        "email": "nonexistent@example.com",
        "password": "AnyPassword!",
    }

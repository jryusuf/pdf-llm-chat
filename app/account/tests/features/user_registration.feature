# Feature: User Registration
#   As a user of the product
#   I want to register with my email and password
#   So that I can create a new account and access the application's features.

Feature: User Registration
  Enable new users to create an account in the system.

  Scenario: Successful registration
    Given the user provides a valid email and a password meeting basic criteria
    When the user attempts to register
    Then the system creates a new user account
    And the password is securely stored
    And the system returns an HTTP 201 Created response

  Scenario: Registration with existing email
    Given a user with the email already exists
    And the user attempts to register with the existing email
    When the user attempts to register
    Then the system returns an HTTP 409 Conflict response

  Scenario: Registration with invalid input
    Given the user provides an invalid email format or a password not meeting basic requirements
    When the user attempts to register
    Then the system returns an HTTP 422 Request response

# Feature: User Login & JWT Generation
#   As a user of the product
#   I want to log in with my email and password
#   So that I can receive a JWT token to authenticate 
#   myself for subsequent API requests.

Feature: User Login & JWT Generation
  Allow registered users to log in and obtain a JWT.

  Scenario: Successful login with valid credentials
    Given a user account is registered
    And the user provides a valid registered email and correct password
    When the user attempts to log in
    Then the system verifies credentials
    And the system generates a JWT
    And the system returns the JWT in the HTTP 200 OK response body

  Scenario: Login attempt with incorrect password
    Given a user account is registered
    And the user provides a valid registered email but incorrect password
    When the user attempts to log in
    Then the system returns an HTTP 401 Unauthorized response

  Scenario: Login attempt with non-existent email
    Given the user attempts to log in with an email not registered in the system
    When the user attempts to log in
    Then the system returns an HTTP 401 Unauthorized response

# Feature: E02-F02
Feature: List User's PDFs
  Allow authenticated users to retrieve a list of their previously uploaded PDFs.

  # User Story: E02-F02-S01
  # As a user of the product
  # I want to see a list of my uploaded PDFs via GET /pdf-list, with pagination
  # So that I can see their names, upload dates, and parsing status efficiently.

  # Use Case: E02-F02-S01-C01
  Scenario: Retrieve list of uploaded PDFs (first page)
    Given a user is authenticated
    And the user has uploaded at least one PDF
    When the user requests their list of PDFs
    Then the system returns an HTTP 200 OK response
    And the response contains a paginated list of PDFs
    And the list contains the user's uploaded PDFs for the first page
    And the PDFs in the list are ordered by upload date descending

  # Use Case: E02-F02-S01-C02
  Scenario: Retrieve list when no PDFs uploaded by user
    Given a user is authenticated
    And the user has not uploaded any PDFs
    When the user requests their list of PDFs
    Then the system returns an HTTP 200 OK response
    And the response contains a paginated list with zero total items

  # Use Case: E02-F02-S01-C03
  Scenario: Retrieve subsequent pages of PDFs using pagination parameters
    Given a user is authenticated
    And the user has uploaded multiple PDFs
    When the user requests the second page of their PDFs with a size of 10
    Then the system returns an HTTP 200 OK response
    And the response contains a paginated list of PDFs
    And the list contains the user's uploaded PDFs for the second page
    And the PDFs in the list are ordered by upload date descending

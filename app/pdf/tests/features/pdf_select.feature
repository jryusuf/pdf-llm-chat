# Feature: E02-F04
Feature: Select PDF for Chat
  Allow users to select a previously uploaded and parsed PDF to be the context for their chat session using a persistent server-side state (MongoDB flag).

  # User Story: E02-F04-S01
  # As a user of the product
  # I want to select a specific PDF that I have uploaded and has been successfully parsed, via POST /pdf-select
  # So that my subsequent chat messages are understood by the system to be in the context of that selected document.

  # Use Case: E02-F04-S01-C01
  Scenario: Successfully select a parsed PDF for chat
    Given a user is authenticated
    And the user has a successfully parsed PDF
    When the user requests to select the PDF for chat
    Then the system updates the PDF's selected status to true
    And the system returns an HTTP 200 OK response

  # Use Case: E02-F04-S01-C02
  Scenario Outline: Attempt to select a PDF that is not yet parsed or parsing failed (<parse_status> status)
    Given a user is authenticated
    And the user has a PDF with parse status <parse_status>
    When the user requests to select the PDF for chat
    Then the system returns an HTTP 409 Conflict or HTTP 400 Bad Request

    Examples: Invalid Parse Statuses
      | parse_status   |
      | UNPARSED       |
      | PARSING        |
      | PARSED_FAILURE |

  # Use Case: E02-F04-S01-C03
  Scenario: Attempt to select a non-existent or unauthorized PDF for chat
    Given a user is authenticated
    And the user attempts to select a non-existent or unauthorized PDF
    When the user requests to select the PDF for chat
    Then the system returns an HTTP 404 Not Found or HTTP 403 Forbidden

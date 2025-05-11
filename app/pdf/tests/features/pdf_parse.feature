# Feature: E02-F03
Feature: Parse PDF Content (Async with Procrastinate)
  Allow users to initiate text extraction from a selected PDF using PyPDF2 via a background task managed by Procrastinate. The parsed text and status are saved.

  # User Story: E02-F03-S01
  # As a user of the product
  # I want to request parsing of my PDF via POST /pdf-parse, have it processed in the background, and be able_to_track_its_status indirectly by observing the 'parse_status' field when I list my PDFs
  # So that the API responds quickly to my parse request, and I can asynchronously know when the PDF is ready for chat or if parsing encountered an issue.

  # Use Case: E02-F03-S01-C01
  Scenario: Successfully initiate PDF parsing for an unparsed PDF
    Given a user is authenticated
    And the user has an unparsed PDF
    When the user requests parsing for the PDF
    Then the system updates the PDF parse status to PARSING
    And the system enqueues a PDF parsing task
    And the system returns an HTTP 202 Accepted response

  # Use Case: E02-F03-S01-C02 - Background task success (typically integration/unit test)
  # Description: The enqueued Procrastinate worker retrieves the PDF binary from GridFS, uses PyPDF2 to extract text content. Stores the extracted text (e.g., in the `parsed_pdf_texts_collection` in MongoDB, linked by `pdf_metadata_id`). Updates the `parse_status` in the corresponding `pdf_metadata_collection` document to 'PARSED_SUCCESS'.

  # Use Case: E02-F03-S01-C03 - Background task failure (typically integration/unit test)
  # Description: The Procrastinate worker encounters an error during parsing (e.g., PDF is corrupt, encrypted, or PyPDF2 error). It updates the `parse_status` in `pdf_metadata_collection` to 'PARSED_FAILURE' and stores a relevant error message in the `parse_error_message` field.

  # Scenario: User observes successful PDF parsing status
  Scenario: User observes successful PDF parsing status
    Given a user is authenticated
    And the user has a PDF with parse status PARSING
    And the background parsing task for the PDF completes successfully
    When the user requests their list of PDFs
    Then the system returns an HTTP 200 OK response
    And the response contains a paginated list of PDFs
    And the list contains the PDF with parse status PARSED_SUCCESS

  # Scenario: User observes failed PDF parsing status
  Scenario: User observes failed PDF parsing status
    Given a user is authenticated
    And the user has a PDF with parse status PARSING
    And the background parsing task for the PDF fails
    When the user requests their list of PDFs
    Then the system returns an HTTP 200 OK response
    And the response contains a paginated list of PDFs
    And the list contains the PDF with parse status PARSED_FAILURE
    And the list contains a parse error message for the PDF

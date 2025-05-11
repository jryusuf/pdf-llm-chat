Feature: PDF File Type Validation and Upload
  Allow authenticated users to upload PDF files, which are stored in MongoDB GridFS with associated metadata, ensuring only PDF files are accepted.

  Scenario: Successful PDF upload with valid PDF type
    Given a user is authenticated
    And the user has a valid PDF file
    When the user attempts to upload the PDF file to /pdf-upload
    Then the system stores the file in GridFS
    And the system stores the metadata in the database
    And the system returns an HTTP 201 Created response with the new PDF's ID

  Scenario: Attempt to upload a non-PDF file type
    Given a user is authenticated
    And the user has a non-PDF file
    When the user attempts to upload the non-PDF file to /pdf-upload
    Then the system rejects the upload
    And the system returns an HTTP 415 Unsupported Media Type or HTTP 400 Bad Request

  Scenario: Attempt to upload PDF without authentication
    Given a user is not authenticated
    And the user has a valid PDF file
    When the user attempts to upload the PDF file to /pdf-upload
    Then the system returns an HTTP 401 Unauthorized response

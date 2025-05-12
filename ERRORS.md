# API Error Documentation

This document outlines the possible domain exceptions and REST errors that can be encountered when interacting with the API, organized by service and URL.

## Account Service

### POST `/account/register`

- **Error:** `UserAlreadyExistsError`
  - **HTTP Status Code:** 409 Conflict
  - **Explanation:** This error occurs when attempting to register a user with an email address that is already registered in the system.
  - **When it happens:** When a user tries to create an account with an email that is already in use.

- **Error:** `ValueError`
  - **HTTP Status Code:** 400 Bad Request
  - **Explanation:** This error indicates that the provided user data is invalid or malformed.
  - **When it happens:** When the user provides data that does not meet the required format or constraints during registration (e.g., invalid email format, weak password).

- **Error:** `Exception`
  - **HTTP Status Code:** 500 Internal Server Error
  - **Explanation:** A general error occurred on the server during the registration process.
  - **When it happens:** An unexpected issue occurred on the server side during user registration.

### POST `/account/login`

- **Error:** `InvalidCredentialsError`
  - **HTTP Status Code:** 401 Unauthorized
  - **Explanation:** This error occurs when the provided email and password do not match a registered user.
  - **When it happens:** When a user attempts to log in with incorrect email or password.

- **Error:** `Exception`
  - **HTTP Status Code:** 500 Internal Server Error
  - **Explanation:** A general error occurred on the server during the login process.
  - **When it happens:** An unexpected issue occurred on the server side during user login.

## Chat Service

### POST `/chat/pdf-chat`

- **Error:** `NoPDFSelectedForChatError`
  - **HTTP Status Code:** 400 Bad Request
  - **Explanation:** This error occurs when a user attempts to send a chat message without having selected a PDF for the chat context.
  - **When it happens:** When a user initiates a chat or sends a message in the chat interface before selecting a PDF.

- **Error:** `PDFNotParsedForChatError`
  - **HTTP Status Code:** 409 Conflict
  - **Explanation:** This error occurs when the selected PDF has not been successfully parsed and processed for chat interactions.
  - **When it happens:** When a user selects a PDF that is still being parsed or failed to parse and attempts to chat with it.

- **Error:** `PDFNotFoundError`
  - **HTTP Status Code:** 404 Not Found
  - **Explanation:** This error occurs when the selected PDF for chat does not exist.
  - **When it happens:** When a user attempts to chat with a PDF that has been deleted or the provided PDF ID is incorrect.

- **Error:** `ChatDomainError`
  - **HTTP Status Code:** 400 Bad Request
  - **Explanation:** A general domain-specific error occurred within the chat service.
  - **When it happens:** Other chat-related domain validation or business logic errors.

- **Error:** `Exception`
  - **HTTP Status Code:** 500 Internal Server Error
  - **Explanation:** A general error occurred on the server during the chat message submission process.
  - **When it happens:** An unexpected issue occurred on the server side while processing a chat message.

### GET `/chat/chat-history`

- **Error:** `Exception`
  - **HTTP Status Code:** 500 Internal Server Error
  - **Explanation:** A general error occurred on the server while retrieving chat history.
  - **When it happens:** An unexpected issue occurred on the server side while fetching the user's chat history.

## PDF Service

### POST `/pdf/pdf-upload`

- **Error:** Unsupported Media Type
  - **HTTP Status Code:** 415 Unsupported Media Type
  - **Explanation:** This error occurs when a file type other than 'application/pdf' is uploaded.
  - **When it happens:** When a user attempts to upload a file that is not a PDF.

- **Error:** `Exception`
  - **HTTP Status Code:** 500 Internal Server Error
  - **Explanation:** A general error occurred on the server during the PDF upload process.
  - **When it happens:** An unexpected issue occurred on the server side during PDF upload.

### GET `/pdf/pdf-list`

- **Error:** `Exception`
  - **HTTP Status Code:** 500 Internal Server Error
  - **Explanation:** A general error occurred on the server while listing PDFs.
  - **When it happens:** An unexpected issue occurred on the server side while fetching the list of user's PDFs.

### POST `/pdf/pdf-parse`

- **Error:** `PDFNotFoundError`
  - **HTTP Status Code:** 404 Not Found
  - **Explanation:** This error occurs when the specified PDF to be parsed does not exist.
  - **When it happens:** When a user requests parsing for a PDF ID that does not exist.

- **Error:** `Exception`
  - **HTTP Status Code:** 500 Internal Server Error
  - **Explanation:** A general error occurred on the server while requesting PDF parsing.
  - **When it happens:** An unexpected issue occurred on the server side while initiating PDF parsing.

### POST `/pdf/pdf-select`

- **Error:** `PDFNotParsedError`
  - **HTTP Status Code:** 409 Conflict
  - **Explanation:** This error occurs when a user attempts to select a PDF for chat that has not been successfully parsed yet.
  - **When it happens:** When a user tries to select a PDF for chat that is still pending parsing or failed to parse.

- **Error:** `PDFNotFoundError`
  - **HTTP Status Code:** 404 Not Found
  - **Explanation:** This error occurs when the specified PDF to be selected for chat does not exist.
  - **When it happens:** When a user attempts to select a PDF for chat using an ID that does not exist.

- **Error:** `Exception`
  - **HTTP Status Code:** 500 Internal Server Error
  - **Explanation:** A general error occurred on the server while selecting a PDF for chat.
  - **When it happens:** An unexpected issue occurred on the server side while selecting a PDF for chat.

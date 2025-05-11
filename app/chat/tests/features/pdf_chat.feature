Feature: Chat with Selected PDF using Gemini Pro (Async LLM Call)
  Enable users to engage in conversations about their selected PDF documents using an LLM integration.

  # User Story: E03-F01-S01
  # As a user of the product
  # I want to send a question via POST /pdf-chat, have the LLM process it with document context in background, and see the response in my chat history
  # So that I can get answers from the LLM without blocking, and all interactions are recorded with PDF context.

  # Use Case: E03-F01-S01-C01
  Scenario: Successfully initiate chat interaction with a selected and parsed PDF
    Given a user is authenticated
    And the user has a successfully parsed PDF selected for chat
    And the user provides a chat message
    When the user submits the chat message via POST /pdf-chat
    Then the system saves the user message and an LLM placeholder in chat history with status PENDING
    And the system enqueues an LLM processing task
    And the system returns an HTTP 202 Accepted response
    And the response contains the initial chat turn with the user message and PENDING LLM response

  # Use Case: E03-F01-S01-C02 (Background task success - typically integration/unit test)
  # Description: The enqueued Procrastinate worker retrieves the user message details (e.g., from chat_logs), fetches the selected PDF's parsed text (from MongoDB `parsed_pdf_texts_collection`). Calls Gemini API (using API key from env). On success, updates the corresponding LLM placeholder entry in `chat_logs` with the response text and sets `llm_status` to 'COMPLETED_SUCCESS'.

  # Use Case: E03-F01-S01-C03 (Background task failure - typically integration/unit test)
  # Description: If the Gemini API call fails (network issue, API error, etc.), the Procrastinate worker attempts a configured number of retries (e.g., from `LLM_RETRY_ATTEMPTS` env var). If all retries fail, it updates the LLM message entry in `chat_logs` with `llm_status='FAILED_RETRIES_EXHAUSTED'` and logs the error details using Loguru.

  Scenario: Attempt to initiate chat interaction when no PDF is selected
    Given a user is authenticated
    And no PDF is selected for chat
    And the user provides a chat message
    When the user submits the chat message via POST /pdf-chat
    Then the system returns an HTTP 400 Bad Request response
    And the response indicates that no PDF is selected for chat

  Scenario: Attempt to initiate chat interaction when the selected PDF is not parsed
    Given a user is authenticated
    And the user has a PDF selected for chat with parse status UNPARSED or PARSING or PARSED_FAILURE
    And the user provides a chat message
    When the user submits the chat message via POST /pdf-chat
    Then the system returns an HTTP 409 Conflict response
    And the response indicates that the selected PDF is not parsed

  Scenario: Attempt to initiate chat interaction when the selected PDF is not found
    Given a user is authenticated
    And the user has selected a PDF that does not exist
    And the user provides a chat message
    When the user submits the chat message via POST /pdf-chat
    Then the system returns an HTTP 404 Not Found response
    And the response indicates that the selected PDF was not found

  # Feature: E03-F01-S02 (Implicit in the above, but could have separate scenarios if needed)
  # User Story: As a system component, I want the LLM call to be processed asynchronously in the background using Procrastinate
  # So that the API remains responsive and the user doesn't have to wait for the LLM response.

  # Feature: E03-F01-S03 (Implicit in the above, but could have separate scenarios if needed)
  # User Story: As a system component, I want chat history to be logged in PostgreSQL
  # So that user interactions and LLM responses are persistently stored and linked to the PDF context.

  # Feature: E03-F01-S04 (Implicit in the above, but could have separate scenarios if needed)
  # User Story: As a system component, I want each question to be treated independently with full PDF text context
  # So that the LLM response is based solely on the current question and the selected PDF content, not previous chat turns.

  # Feature: E03-F01-S05 (Implicit in the above, but could have separate scenarios if needed)
  # User Story: As a system component, I want chat messages to be linked to the PDF filename for context
  # So that it's clear which PDF was being discussed in each chat session.

  # Feature: E03-F01-S06 (Implicit in the above, but could have separate scenarios if needed)
  # User Story: As a system component, I want the background task to handle LLM API errors, retries, and final failure
  # So that the system is resilient to temporary LLM API issues and logs failures appropriately.

  # Feature: E03-F01-S07 (Implicit in the above, but could have separate scenarios if needed)
  # User Story: As a system component, I want to retrieve chat history via GET /chat-history with pagination
  # So that users can view their past conversations efficiently.

  Scenario: Successfully retrieve paginated chat history
    Given a user is authenticated
    And the user has previous chat history entries
    When the user requests their chat history via GET /chat-history
    Then the system returns an HTTP 200 OK response
    And the response contains a paginated list of chat history entries
    And the chat history entries are ordered by timestamp descending

  Scenario: Retrieve chat history when no entries exist for the user
    Given a user is authenticated
    And the user has no previous chat history entries
    When the user requests their chat history via GET /chat-history
    Then the system returns an HTTP 200 OK response
    And the response contains a paginated list with zero total items

  Scenario: Retrieve subsequent pages of chat history using pagination parameters
    Given a user is authenticated
    And the user has multiple pages of chat history entries
    When the user requests the second page of their chat history with a size of 10
    Then the system returns an HTTP 200 OK response
    And the response contains a paginated list of chat history entries
    And the list contains the user's chat history entries for the second page
    And the chat history entries are ordered by timestamp descending

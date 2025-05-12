# Document Chat Assistant

This project is a RESTful API built with FastAPI that allows users to upload PDF documents, extract their text content, and chat with the document's content using a Gemini-based LLM integration.

## Features

*   **User Authentication:** JWT-based authentication for secure access.
*   **PDF Management:** Upload, list, parse, and select PDF documents.
*   **LLM Chat:** Engage in conversations about selected PDF documents using the Gemini API.
*   **Data Storage:** PostgreSQL for user and chat history, MongoDB (GridFS) for PDF files and metadata.
*   **Containerization:** Docker support for easy setup and deployment.

## Architecture

For a detailed overview of the system's architecture, see the [ARCHITECTURE.md](ARCHITECTURE.md) file.

## Tech Stack

*   **Backend Framework:** FastAPI
*   **Databases:** PostgreSQL, MongoDB
*   **PDF Processing:** PyPDF2
*   **LLM Integration:** Gemini API (via curl)
*   **Authentication:** JWT
*   **Containerization:** Docker

## Setup and Installation

* Clone the repository:
  ```bash
  git clone https://github.com/jryusuf/pdf-llm-chat
  cd pdf-llm-chat
  ```

## Running the Project using Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t document-chat-assistant .
    ```
2.  **Run the Docker container:**
    If using `docker-compose.yml`, you can use:
    ```bash
    docker-compose up --build
    ```
    Otherwise, you can run the container directly, ensuring you map ports and provide environment variables:
    ```bash
    docker run -p 8000:8000 --env-file .env document-chat-assistant
    ```
    (Adjust port mapping if necessary)

The API should be accessible at `http://localhost:8000`.

## Development and Testing with Makefile

The project includes a `Makefile` to streamline common development and testing tasks. Ensure you have `make` installed on your system.

Here are the available targets:

*   `make all`: Runs `setup-dev` and `install-dev`. This is the default target.
*   `make setup-dev`: Creates a Python virtual environment in the `./venv` directory.
*   `make install-dev`: Installs the development dependencies listed in `requirements-dev.txt` into the virtual environment.
*   `make run-server`: Starts the FastAPI development server using Uvicorn with auto-reloading enabled. The server runs on `http://0.0.0.0:8000`.
*   `make test`: Runs all tests, including pytest unit/integration tests and behave feature tests for all modules (account, chat, pdf). Includes coverage reporting.
*   `make clean`: Removes the virtual environment directory (`./venv`), `__pycache__` directories, `.pyc`, `.pyo`, `.pytest_cache`, and `.coverage` files.

To use the Makefile targets, first ensure you have run `make all` or `make setup-dev` followed by `make install-dev`. Then, you can run commands like:

```bash
make run-server
make test
```

## Environment Variables

Create a `.env` file in the project root with the following variables, based on the `.env.example` file:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_SYSTEM_PROMPT='Your desired system prompt for the AI assistant.'
```

*   `GEMINI_API_KEY`: Your API key for the Google Gemini API.
*   `GEMINI_SYSTEM_PROMPT`: The initial prompt used to configure the AI assistant's behavior.

Note: Additional environment variables for database connections (`DATABASE_URL`, `MONGO_URL`) are configured in `app/core/config.py` and may need to be set depending on your deployment method (e.g., if not using the provided `docker-compose.yml`).

## Known Issues and Limitations

*   LLM requests and parsing currently implemented as async methods, this can move to background tasks or using celery/procastinator workers

## Improvement Ideas (Optional)

*   Fix feature test authentication errors
*   Add support for other document types (e.g., DOCX).
*   Improve error handling and logging details.
*   Implement rate limiting for API endpoints.
*   Add more advanced chat features (e.g., streaming responses).
*   Seperate dependency between chat and pdf services to reduce coupling
*   Deploy each service as seperate microservices
*   Add API gateway useing Ngnix or other reverse proxies
## API Usage Examples

(Note: Replace `your_token` with the actual JWT token obtained from the login endpoint)

**1. Register a new user:**

```bash
curl -X POST \
  http://localhost:8000/register \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "testuser@example.com",
    "password": "securepassword"
  }'
```

**2. Login a user:**

```bash
curl -X POST \
  http://localhost:8000/login \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "testuser@example.com",
    "password": "securepassword"
  }'
```

**3. Upload a PDF:**

```bash
curl -X POST \
  http://localhost:8000/pdf-upload \
  -H 'Authorization: Bearer your_token' \
  -F 'file=@/path/to/your/document.pdf'
```

**4. List uploaded PDFs:**

```bash
curl -X GET \
  http://localhost:8000/pdf-list \
  -H 'Authorization: Bearer your_token'
```

**5. Parse a PDF (replace `pdf_id` with the actual ID):**

```bash
curl -X POST \
  http://localhost:8000/pdf-parse \
  -H 'Authorization: Bearer your_token' \
  -H 'Content-Type: application/json' \
  -d '{
    "pdf_id": "your_pdf_id"
  }'
```

**6. Select a PDF for chat (replace `pdf_id` with the actual ID):**

```bash
curl -X POST \
  http://localhost:8000/pdf-select \
  -H 'Authorization: Bearer your_token' \
  -H 'Content-Type: application/json' \
  -d '{
    "pdf_id": "your_pdf_id"
  }'
```

**7. Chat with the selected PDF:**

```bash
curl -X POST \
  http://localhost:8000/pdf-chat \
  -H 'Authorization: Bearer your_token' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What is this document about?"
  }'
```

**8. Get chat history:**

```bash
curl -X GET \
  http://localhost:8000/chat-history \
  -H 'Authorization: Bearer your_token'
```

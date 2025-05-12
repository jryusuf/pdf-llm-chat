# Document Chat Assistant

This project is a RESTful API built with FastAPI that allows users to upload PDF documents, extract their text content, and chat with the document's content using a Gemini-based LLM integration.

## Features

*   **User Authentication:** JWT-based authentication for secure access.
*   **PDF Management:** Upload, list, parse, and select PDF documents.
*   **LLM Chat:** Engage in conversations about selected PDF documents using the Gemini API.
*   **Data Storage:** PostgreSQL for user and chat history, MongoDB (GridFS) for PDF files and metadata.
*   **Containerization:** Docker support for easy setup and deployment.

## Tech Stack

*   **Backend Framework:** FastAPI
*   **Databases:** PostgreSQL, MongoDB
*   **PDF Processing:** PyPDF2
*   **LLM Integration:** Gemini API (via OpenAI Python SDK compatible endpoint)
*   **Authentication:** JWT
*   **Containerization:** Docker

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd pdf-llm-chat
    ```
2.  **Set up environment variables:**
    Create a `.env` file in the project root directory based on the example provided in the "Environment Variables" section.
3.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```
4.  **Database Setup:**
    Ensure PostgreSQL and MongoDB instances are running and accessible as configured in your environment variables. You may need to run database migrations for PostgreSQL (details on this would depend on the ORM setup, likely using Alembic if present, or SQLAlchemy directly).

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

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
DATABASE_URL=postgresql://user:password@host:port/database
MONGO_URI=mongodb://user:password@host:port/database
JWT_SECRET_KEY=your_jwt_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GEMINI_API_KEY=your_gemini_api_key
```

*   `DATABASE_URL`: Connection string for PostgreSQL.
*   `MONGO_URI`: Connection string for MongoDB.
*   `JWT_SECRET_KEY`: Secret key for signing JWT tokens.
*   `ALGORITHM`: Algorithm used for JWT signing (e.g., HS256).
*   `ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration time for access tokens in minutes.
*   `GEMINI_API_KEY`: Your API key for the Gemini Pro API.

## Known Issues and Limitations

*   (Add any known issues or limitations here based on development)

## Improvement Ideas (Optional)

*   Implement unit tests for all modules.
*   Add support for other document types (e.g., DOCX).
*   Improve error handling and logging details.
*   Implement rate limiting for API endpoints.
*   Add more advanced chat features (e.g., streaming responses).

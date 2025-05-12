# Document Chat Assistant Architecture

This document describes the architecture of the Document Chat Assistant system, which allows users to upload PDF documents and chat about their content using a Large Language Model.

## System Context

The following diagram illustrates the system context, showing the main user and the external system it interacts with.

```mermaid
C4Context 
    title System Context Diagram for Document Chat Assistant
Person(user, "User", "uploads PDFs and chats about them.")
System_Boundary(doc_chat_assistant_system, "Document Chat Assistant") {
  System(doc_chat_assistant, "Document Chat Assistant", "")
}
System_Ext(gemini_api, "Google Gemini API", "Large Language Model")

Rel(user, doc_chat_assistant, "Interacts via REST API", "HTTPS/JSON")
Rel(doc_chat_assistant, gemini_api, "Sends Prompts & Receives Responses", "HTTPS/JSON, Gemini API SDK")

UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

The **User** interacts with the **Document Chat Assistant** system by uploading PDF files and engaging in chat conversations about the document content. The Document Chat Assistant utilizes the **Google Gemini API** as the Large Language Model to process chat prompts and generate responses based on the uploaded documents.

## Container Diagram

The container diagram provides a higher-level view of the system, showing the main containers and their interactions.

```mermaid
C4Container 
    title Container Diagram for Document Chat Assistant (Simplified)
Person_Ext(user, "User", "Product User")
System_Ext(gemini_api_ext, "Google Gemini API", "LLM Service")

System_Boundary(doc_chat_assistant_system, "Document Chat Assistant System") {
  Container(web_app, "FastAPI Web Application", "Python/FastAPI/Uvicorn", "Handles HTTP API requests")
  ContainerDb(postgres_db, "PostgreSQL Database", "PostgreSQL 15", "Stores user accounts, chat history")
  ContainerDb(mongo_db, "MongoDB Database", "MongoDB 8", "Stores PDF and text")

  Rel(web_app, postgres_db, "Reads/Writes to", "SQLAlchemy (asyncpg)")
  Rel(web_app, mongo_db, "Reads/Writes to", "Pymongo (async)")
  Rel(web_app, gemini_api_ext, "Sends Prompts, Receives LLM Responses", "HTTPS/JSON, Gemini API SDK")
}

Rel(user, web_app, "Sends HTTPS Requests To", "HTTPS/JSON")

UpdateElementStyle(web_app, $bgColor="Blue")
UpdateElementStyle(postgres_db, $bgColor="Orchid")
UpdateElementStyle(mongo_db, $bgColor="Orchid")
UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

The system consists of a **FastAPI Web Application** that serves as the main entry point for user interactions. It communicates with two databases: a **PostgreSQL Database** for storing user accounts and chat history, and a **MongoDB Database** for storing PDF documents and their parsed text content. The Web Application also interacts with the external **Google Gemini API** for LLM capabilities.

## FastAPI Application Internal Structure

The FastAPI Web Application is structured into several internal service modules, as shown in the diagram below.

```mermaid
C4Container 
title FastAPI Application Container - Internal Service Modules View
%% External Actors and Systems that the App Container interacts with
Person_Ext(user_ext, "User")
ContainerDb_Ext(postgres_db_ext, "PostgreSQL Database")
ContainerDb_Ext(mongo_db_ext, "MongoDB Database")
System_Ext(gemini_api_ext, "Google Gemini API")

Container_Boundary(web_app_container, "FastAPI Web Application Container", "Python/FastAPI/Uvicorn") {
  %% Core/Shared Components within the App Container
  Component(procrastinate_core, "Procrastinate Core Setup", "app.core.procrastinate_app", "Manages Background Task Queue")
  %%Component(shared_utils_lib, "Shared Utilities", "app.lib", "Common Pydantic Bases, Utils")

  %% Logical Service Modules as High-Level Components/Boundaries within the App
  System_Boundary(account_module, "Account Service Module", "Handles User Registration & Login") {
    Component(acc_components_placeholder, "Account Components", "Controller, App Service, Domain, Infra", "Internal logic for account management")
  }
  System_Boundary(pdf_module, "PDF Service Module", "Handles PDF Upload, Parsing, Selection") {
    Component(pdf_components_placeholder, "PDF Components", "Controller, App Service, Domain, Infra, Parse Task", "Internal logic for PDF operations")
  }
  System_Boundary(chat_module, "Chat Service Module", "Handles Chat Messages & History") {
    Component(chat_components_placeholder, "Chat Components", "Controller, App Service, Domain, Infra, LLM Task", "Internal logic for chat functionality")
  }
}

%% Styling for clarity
UpdateElementStyle(auth_lib, $bgColor="LightCyan")
UpdateElementStyle(error_handling_core, $bgColor="MistyRose")
UpdateElementStyle(logging_core, $bgColor="Thistle")
UpdateElementStyle(procrastinate_core, $bgColor="Lavender")
UpdateElementStyle(shared_utils_lib, $bgColor="WhiteSmoke")
UpdateElementStyle(account_module, $bgColor="Blue", $borderColor="DarkBlue")
UpdateElementStyle(pdf_module, $bgColor="Orange", $borderColor="DarkGreen")
UpdateElementStyle(chat_module, $bgColor="Green", $borderColor="SaddleBrown")

%% Make placeholder components less visually prominent if needed or style them
UpdateElementStyle(acc_components_placeholder, $bgColor="White", $borderColor="LightGray", $fontColor="Gray")
UpdateElementStyle(pdf_components_placeholder, $bgColor="White", $borderColor="LightGray", $fontColor="Gray")
UpdateElementStyle(chat_components_placeholder, $bgColor="White", $borderColor="LightGray", $fontColor="Gray")

UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="3")
```

The FastAPI application is organized into distinct service modules: Account, PDF, and Chat. It also includes core components for managing background tasks (Procrastinate).

### Account Service Module

The Account service module handles user registration and login. Its internal structure follows a layered architecture.

```mermaid
C4Component
  title Account Service Module (within FastAPI App)

  %% External Actors and Systems relevant to Account Service
  Person_Ext(user, "User")
  Container_Ext(postgres_db_ext, "PostgreSQL DB", "Stores User Account data")

  %% Shared Utilities/Libraries (External to the module's layers but used by them)

  Container_Boundary(web_app_container, "FastAPI Web Application Container") {
    System_Boundary(account_service_module, "Account Service Module") {
      %% Architectural Layers as Components
      Component(acc_controller_layer, "Controller Layer (Account)", "Routers, Dependencies", "Handles HTTP requests")
      Component(acc_infrastructure_layer, "Infrastructure Layer (Account)", "SQLAlchemyUserRepository", "Implements Repository Interfaces")
      Component(acc_application_layer, "Application Layer (Account)", "Services, Schemas", "Orchestrates use cases")
      Component(acc_domain_layer, "Domain Layer (Account)", "Models, Exceptions", "Core business logic, entities, persistence contracts.")

      %% Layer Interactions
      Rel(acc_controller_layer, acc_application_layer, "Calls Use Cases / Application Services")

      Rel(acc_application_layer, acc_domain_layer, "Uses Domain Models & Repository Interfaces")

      Rel(acc_domain_layer, acc_infrastructure_layer, "Repository Interfaces Implemented by")

      Rel(acc_infrastructure_layer, postgres_db_ext, "Reads/Writes User Data")
    }
  }

  %% External Interactions
  Rel(user, acc_controller_layer, "Sends HTTP Requests (Register, Login)")


  %% Styling for Layers
  UpdateElementStyle(acc_controller_layer, $bgColor="Blue")
  UpdateElementStyle(acc_application_layer, $bgColor="Green")
  UpdateElementStyle(acc_domain_layer, $bgColor="Orange")
  UpdateElementStyle(acc_infrastructure_layer, $bgColor="Purple")

  UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="3")
```

The **Controller Layer** handles incoming HTTP requests related to account management. The **Application Layer** orchestrates the use cases, utilizing the **Domain Layer** for core business logic and interacting with the **Infrastructure Layer** to persist data in the **PostgreSQL Database**.

### Chat Service Module

The Chat service module manages chat messages and history. It interacts with the Gemini API and both databases.

```mermaid
C4Component
  title Chat Service Module (within FastAPI App)

  %% External Actors and Systems relevant to Chat Service
  Person_Ext(user, "User")
  System_Ext(gemini_api_ext, "Google Gemini API", "LLM Service for generating responses")
  Container_Ext(postgres_db_ext_chat, "PostgreSQL DB (for Chat)", "Stores Chat History")
  Container_Ext(mongo_db_ext, "MongoDB", "Stores PDF data")

  %% Shared Utilities/Libraries & Interfaces from other modules


  Container_Boundary(web_app_container, "FastAPI Web Application Container") {
    System_Boundary(chat_service_module, "Chat Service Module") {
      %% Architectural Layers as Components
      Component(chat_controller_layer, "Controller Layer (Chat)", "Routers, dependencies", "Handles HTTP requests")
      Component(chat_application_layer, "Application Layer (Chat)", "Services, Schemas, LLM Task Def.", "Orchestrates chat use cases ")
      Component(chat_domain_layer, "Domain Layer (Chat)", "Model, Exceptions", "Core chat logic, entity, persistence contract.")
      Component(chat_infrastructure_layer, "Infrastructure Layer (Chat)", "SQLAlchemyChatRepository", "Implements Repository Interfaces")

      %% Layer Interactions
      Rel(chat_controller_layer, chat_application_layer, "Calls Use Cases / Application Services")

      Rel(chat_application_layer, chat_domain_layer, "Uses Domain Models & Own Repository Interface")
      Rel(chat_application_layer, ipdf_repository_interface, "Uses PDF Repository Interface")

      Rel(chat_domain_layer, chat_infrastructure_layer, "Repository Interfaces ")

      Rel(chat_infrastructure_layer, postgres_db_ext_chat, "Reads/Writes")

      Rel(chat_application_layer, gemini_api_ext, "LLM Task calls")


    }
    System_Boundary(pdf_service_module, "PDF Service Module"){
      Component_Ext(ipdf_repository_interface, "IPDFRepository (from PDF Module)", "app.pdf.domain.interfaces.IPDFRepository", "Contract to fetch PDF data (selected PDF, parsed text).")

      Rel(ipdf_repository_interface, mongo_db_ext, "Reads PDF text data")
    }
  }

  %% External Interactions
  Rel(user, chat_controller_layer, "Sends HTTP Requests for Chat Operations")

  %% Styling for Layers
  UpdateElementStyle(chat_controller_layer, $bgColor="Blue")
  UpdateElementStyle(chat_application_layer, $bgColor="Green")
  UpdateElementStyle(chat_domain_layer, $bgColor="Orange")
  UpdateElementStyle(chat_infrastructure_layer, $bgColor="Purple")

  UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="2")
```

The **Chat Service Module**'s **Controller Layer** handles chat-related requests. The **Application Layer** orchestrates chat flows, interacting with the **Domain Layer**, the **Infrastructure Layer** (for PostgreSQL chat history), and the **PDF Service Module** (via the `IPDFRepository` interface) to access PDF data. It also makes calls to the **Google Gemini API** for generating chat responses.

### PDF Service Module

The PDF service module is responsible for handling PDF uploads, parsing, and selection.

```mermaid
C4Component
  title PDF Service Module (within FastAPI App)

  %% External Actors and Systems relevant to PDF Service
  Person_Ext(user, "User")
  Container_Ext(mongo_db_ext, "MongoDB", "Stores PDF data")

  %% Shared Utilities/Libraries


  Container_Boundary(web_app_container, "FastAPI Web Application Container") {
    System_Boundary(pdf_service_module, "PDF Service Module") {
      %% Architectural Layers as Components
      Component(pdf_controller_layer, "Controller Layer (PDF)", "Routers, dependencies", "Handles HTTP requests")
     %% Component_Ext(pypdf2_lib, "PyPDF2 Library", "PyPDF2", "For PDF text extraction.")
      Component(pdf_infrastructure_layer, "Infrastructure Layer (PDF)", "MongoPDFRepository", "Implements Repository Interfaces")
      Component(pdf_application_layer, "Application Layer (PDF)", "Services, Schemas", "Orchestrates PDF use cases")
      Component(pdf_domain_layer, "Domain Layer (PDF)", "Model, Exceptions", "Core PDF logic, entity, persistence contract.")

      %% Layer Interactions
      Rel(pdf_controller_layer, pdf_application_layer, "Calls Use Cases / Application Services")

      Rel(pdf_application_layer, pdf_domain_layer, "Uses Domain Models & Repository Interfaces")
      %%Rel(pdf_application_layer, pypdf2_lib, "Uses (in parse task logic) for Text Extraction")

      Rel(pdf_domain_layer, pdf_infrastructure_layer, "Repository Interfaces Implemented by")

      Rel(pdf_infrastructure_layer, mongo_db_ext, "Reads/Writes PDF Data (Meta, GridFS, Parsed Text)")

    }
  }

  %% External Interactions
  Rel(user, pdf_controller_layer, "Sends HTTP Requests for PDF Operations")

  %% Styling for Layers
  UpdateElementStyle(pdf_controller_layer, $bgColor="Blue")
  UpdateElementStyle(pdf_application_layer, $bgColor="Green")
  UpdateElementStyle(pdf_domain_layer, $bgColor="Orange")
  UpdateElementStyle(pdf_infrastructure_layer, $bgColor="Purple")

  UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

The **PDF Service Module**'s **Controller Layer** handles PDF-related requests. The **Application Layer** orchestrates the PDF use cases, interacting with the **Domain Layer** and the **Infrastructure Layer** to store and retrieve PDF data (metadata, GridFS content, and parsed text) from **MongoDB**.

## Technologies Used

*   **FastAPI:** Web framework for building the API.
*   **Uvicorn:** ASGI server for running the FastAPI application.
*   **SQLAlchemy:** ORM for interacting with the PostgreSQL database.
*   **Psycopg:** PostgreSQL adapter for SQLAlchemy.
*   **Motor:** Asynchronous driver for MongoDB.
*   **PostgreSQL:** Relational database for user accounts and chat history.
*   **MongoDB:** Document database for storing PDF data and parsed text.
*   **Google Gemini API:** Large Language Model for chat functionality.
*   **Pydantic:** Data validation and settings management.
*   **Loguru:** Logging library.
*   **Procrastinate:** Background task queue.

## Data Models

*   **User Accounts:** Stored in the PostgreSQL database.
*   **Chat History:** Stored in the PostgreSQL database.
*   **PDF Data:** Stored in the MongoDB database, including metadata, the PDF file content (likely in GridFS), and the parsed text content.

## Key Features/Flows

*   **User Registration and Login:** Users can create accounts and log in to the system.
*   **PDF Upload and Processing:** Users can upload PDF files, which are then processed (parsed for text) and stored.
*   **PDF Selection:** Users can select a previously uploaded PDF to chat about.
*   **Chat Interaction:** Users can send messages and receive responses from the AI assistant based on the selected PDF's content.

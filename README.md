# Sentinel AI

Sentinel AI is a demonstration project showcasing an AI agent that leverages Permit.io for fine-grained access control within a Retrieval-Augmented Generation (RAG) workflow. Users can interact with an AI assistant to ask questions about documents, but the AI's responses are constrained by the user's permissions, ensuring that sensitive information is only accessible to authorized individuals.

The project consists of:

1.  **Backend (FastAPI & Python):** Handles user authentication (simulated via user selection), document retrieval based on permissions, query embedding generation, interaction with a Generative AI model (Google Gemini), and communication with Permit.io for authorization checks.
2.  **Frontend (Angular):** Provides a chat interface for users to interact with the Sentinel AI agent, select different user profiles (simulating login), and view accessible documents based on the selected user's role.
3.  **Permit.io Integration:** Manages policies, roles, and resource instances (documents with sensitivity attributes) to enforce access control dynamically.
4.  **Vector Database (PostgreSQL with pgvector):** Stores document embeddings for efficient similarity search during the RAG process.

## Features

- **Role-Based Access Control (RBAC) & Attribute-Based Access Control (ABAC):** Utilizes Permit.io to control access to documents based on user roles and document sensitivity attributes.
- **Retrieval-Augmented Generation (RAG):** Uses a vector database and generative AI to answer user questions based on the content of accessible documents.
- **Dynamic Permissions:** The AI agent only considers documents the current user is permitted to read when generating answers.
- **User Simulation:** Frontend allows switching between predefined user profiles (Manager, Employee, User) with different access levels.
- **Document Processing:** Scripts automatically process markdown documents, generate embeddings, store them in the database, and sync them as resource instances in Permit.io.

## Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose
- [Python](https://www.python.org/downloads/) (>= 3.10 recommended)
- [Node.js](https://nodejs.org/) and npm (for the frontend)
- A [Permit.io](https://www.permit.io/) account and API Key
- A [Google AI API Key](https://aistudio.google.com/app/apikey) (for Gemini embeddings and generation)

## Environment Setup

1.  **Clone the repository:**

    ```bash
    git clone git@github.com:ypk46/sentinel-ai-permit-challenge.git
    cd sentinel-ai-permit-challenge
    ```

2.  **Create a `.env` file** in the project root directory (`/Users/ypk/Dev/Personal/sentinel-ai`) and add the following environment variables:

    ```dotenv
    # Permit.io Configuration
    PERMIT_API_KEY=your_permit_io_api_key  # Obtain from your Permit.io dashboard
    PERMIT_PDP_URL=http://localhost:7766   # Default local PDP URL

    # Google AI API Key
    GOOGLE_API_KEY=your_google_ai_api_key # Obtain from Google AI Studio

    # Database Connection (matches docker-compose.yml)
    DATABASE_URL=postgresql://postgres:super_secret@localhost:5432/sentinel_db
    ```

    Replace `your_permit_io_api_key` and `your_google_ai_api_key` with your actual keys.

## Running Locally

1.  **Start Infrastructure (Database & Permit PDP):**
    Open a terminal in the project root and run:

    ```bash
    docker-compose up -d
    ```

    This will start a PostgreSQL container with the pgvector extension and a Permit.io Policy Decision Point (PDP) container.

2.  **Set up Backend:**

    - **Install Python dependencies:**
      ```bash
      pip install -r requirements.txt
      ```
    - **Initialize the database schema:**
      ```bash
      python scripts/setup_db.py
      ```
    - **Set up Permit.io policies, roles, and users:**
      ```bash
      python scripts/setup_policy.py
      ```
      This script defines the `document` resource, actions (`read`, `summarize`), sensitivity attribute, roles (`manager`, `employee`, `user`), and assigns permissions based on document sensitivity. It also creates sample users for each role.
    - **Process documents for RAG and Permit.io:**
      ```bash
      python scripts/process_documents.py
      ```
      This script reads markdown files from the `documents/` directory, generates embeddings using Google Gemini, stores the content and embeddings in the database, and creates corresponding resource instances in Permit.io with their sensitivity level.

3.  **Run the Backend Server:**

    ```bash
    fastapi dev run.py
    ```

    The FastAPI server will start on `http://localhost:8000`.

4.  **Set up and Run Frontend:**

    - **Navigate to the web directory:**
      ```bash
      cd web
      ```
    - **Install Node.js dependencies:**
      ```bash
      npm install
      ```
    - **Start the Angular development server:**
      ```bash
      npm start
      ```
      The frontend application will be available, usually at `http://localhost:4200`.

5.  **Access the Application:**
    Open your web browser and navigate to `http://localhost:4200`. You can now interact with the Sentinel AI agent and switch between user profiles to see how access control affects the available documents and the AI's responses.

## Project Structure

```
.
├── docker-compose.yml      # Docker configuration for DB and PDP
├── documents/              # Sample markdown documents for RAG
├── requirements.txt        # Python backend dependencies
├── run.py                  # Entry point for backend server
├── scripts/                # Setup and processing scripts
│   ├── db_init.sh          # DB initialization script (used by Docker)
│   ├── process_documents.py# Processes documents, generates embeddings, syncs Permit.io
│   ├── setup_db.py         # Creates database table
│   └── setup_policy.py     # Configures Permit.io resources, roles, policies
├── server/                 # Backend FastAPI application
│   ├── main.py             # FastAPI app definition, endpoints
│   └── models.py           # Pydantic models for API requests/responses
└── web/                    # Frontend Angular application
    ├── angular.json        # Angular project configuration
    ├── package.json        # Frontend dependencies
    └── src/                # Frontend source code
        ├── app/            # Core application components
        ├── environments/   # Environment configuration (API URL)
        └── ...
```

## How it Works

1.  **User Interaction:** The user selects a profile (Manager, Employee, User) and asks a question via the chat interface.
2.  **Backend Query:** The frontend sends the user's query and selected `user_key` to the backend `/query` endpoint.
3.  **Permission Check:** The backend calls `get_valid_documents(user_key, "read")` which queries the Permit.io PDP to determine which document keys the user has `read` permission for, considering their role and the document's sensitivity attribute.
4.  **RAG - Retrieval:** The backend generates an embedding for the user's query and searches the vector database for relevant document chunks, _filtering_ the search results to only include chunks from documents the user is permitted to read (obtained in the previous step).
5.  **RAG - Generation:** The retrieved document chunks are combined with the original query and sent as context to the Google Gemini model.
6.  **Response:** The AI generates an answer based _only_ on the permitted context. The backend returns the answer and the keys of the source documents used to the frontend.
7.  **Display:** The frontend displays the AI's response. The sidebar also dynamically lists documents accessible to the currently selected user by calling the `/documents` endpoint, which also performs a permission check.

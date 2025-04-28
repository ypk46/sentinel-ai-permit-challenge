import logging
import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from google import genai
from google.genai import types
from permit import Permit
from pgvector.psycopg import Vector, register_vector
from psycopg import connect
from psycopg.rows import dict_row

from server.models import QueryRequest, QueryResponse, UserListResponse

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PERMIT_API_KEY = os.getenv("PERMIT_API_KEY")
PERMIT_PDP_URL = os.getenv("PERMIT_PDP_URL", "http://localhost:7766")
DATABASE_URL = os.getenv("DATABASE_URL")
PROMPT_TEMPLATE = """
Answer the question based on the context provided. Keep your answers concise and straight to the point.
The context may contain multiple documents, and you should use the most relevant information to answer the question.
The context is in markdown format, and you should not include any markdown formatting in your answer.
If the context does not contain enough information to answer the question, say "Sorry, I may not have enough information to answer this question.":

Context:
{context}

Question:
{question}
"""

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sentinel AI",
    description="AI agent with chat boundaries defined by policies.",
    version="0.1.0",
)


permit = Permit(token=PERMIT_API_KEY, pdp=PERMIT_PDP_URL)

genai_client = genai.Client(api_key=GOOGLE_API_KEY)


def generate_embedding(content: str):
    """
    Generate embedding for the given content using Google GenAI.

    Args:
        content (str): The content to generate embedding for.

    Returns:
        list: Embedding values for the content.
    """
    # Initialize Google GenAI client
    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Generate embedding for the chunk
    embedding_result = client.models.embed_content(
        model="gemini-embedding-exp-03-07",
        contents=content,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT", output_dimensionality=1536
        ),
    )

    # Extract the embedding values
    [embeddings] = embedding_result.embeddings
    return embeddings.values


def get_valid_documents(user_key: str, action: str):
    """
    Get a list of valid documents for a user based on their permissions.

    Args:
        user_key (str): The key of the user.
        action (str): The action to check permissions for.

    Returns:
        list: A list of valid document keys for the user.
    """
    valid_docs = []

    # Direct call to Permit PDP since ABAC user permissions is not supported in the SDK.
    url = f"{PERMIT_PDP_URL}/user-permissions"

    headers = {
        "Authorization": f"Bearer {PERMIT_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "user": {
            "key": user_key,
        },
        "resource_types": ["document"],
        "context": {"enable_abac_user_permissions": True},
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()

            for key, value in data.items():
                if f"document:{action}" in value.get("permissions", []):
                    valid_docs.append(key.replace("document:", ""))
    except Exception:
        logger.exception("Error fetching user permissions.")

    return valid_docs


def retrieve_documents(query_embedding: list, valid_docs: list):
    """
    Retrieve documents based on the query and valid document keys.

    Args:
        query_embedding (list): The embedding of the query.
        valid_docs (list): A list of valid document keys.

    Returns:
        list: A list of documents that match the query.
    """
    # Connect to the PostgreSQL database
    conn = connect(DATABASE_URL, row_factory=dict_row)
    register_vector(conn)

    # Create a cursor object
    cur = conn.cursor()

    # Insert the document into the database
    cur.execute(
        """
        SELECT content, key, (embedding <-> %s) AS distance FROM documents
        WHERE key = ANY(%s)
        ORDER BY distance
        LIMIT 2;
        """,
        (Vector(query_embedding), valid_docs),
    )

    # Fetch all results
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


def generate_answer(documents: list, query: str):
    """
    Generate an answer based on the retrieved documents.

    Args:
        documents (list): A list of documents to generate an answer from.

    Returns:
        str: The generated answer.
    """
    response = genai_client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction="You are a helpful assistant that provides information based on the documents provided.",
        ),
        contents=PROMPT_TEMPLATE.format(
            context="\n".join([doc["content"] for doc in documents]),
            question=query,
        ),
    )

    return response.text


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Process a query and return the response.
    """
    # Get the valid documents for the user
    valid_docs = get_valid_documents(request.user_key, "read")

    # Generate the embedding for the query
    query_embedding = generate_embedding(request.query)

    # Retrieve documents based on the query and valid document keys
    documents = retrieve_documents(query_embedding, valid_docs)

    # Generate an answer based on the retrieved documents
    answer = generate_answer(documents, request.query)

    response = {
        "answer": answer,
        "sources": [d.get("key") for d in documents],
    }

    return response


@app.get("/users", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of users per page"),
):
    """
    Get a list of users.

    Args:
        page (int): The page number to retrieve.
        page_size (int): The number of users per page.

    Returns:
        list: A list of users.
    """
    users = await permit.api.users.list(page=page, per_page=page_size)

    data = [
        {
            "key": user.key,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.roles[0].role,
        }
        for user in users.data
    ]

    return {"data": data, "total": len(data), "page": page, "page_size": page_size}


@app.get("/documents")
async def get_documents():
    """
    Get a list of documents.

    Returns:
        list: A list of documents.
    """
    # Connect to the PostgreSQL database
    conn = connect(DATABASE_URL, row_factory=dict_row)
    register_vector(conn)

    # Create a cursor object
    cur = conn.cursor()

    # Fetch all documents
    cur.execute("SELECT id, content, title, key, sensitivity FROM documents;")
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results

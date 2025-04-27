import asyncio
import glob
import hashlib
import logging
import os

import frontmatter
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pgvector.psycopg import register_vector
from psycopg import connect

from permit import Permit


load_dotenv()

DOCS_DIR = "documents"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
PERMIT_API_KEY = os.getenv("PERMIT_API_KEY")
PERMT_PDP_URL = os.getenv("PERMIT_PDP_URL", "http://localhost:7766")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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


def insert_document_to_db(content: str, title: str, key: str, embedding: list):
    """
    Insert the document into the PostgreSQL database.

    Args:
        content (str): The content of the document.
        title (str): The title of the document.
        key (str): The key of the document.
        embedding (list): The embedding of the document.
    """
    # Connect to the PostgreSQL database
    conn = connect(DATABASE_URL)
    register_vector(conn)

    # Create a cursor object
    cur = conn.cursor()

    # Insert the document into the database
    cur.execute(
        """
        INSERT INTO documents (content, title, key, embedding)
        VALUES (%s, %s, %s, %s);
        """,
        (content, title, key, embedding),
    )

    # Commit the changes and close the connection
    conn.commit()
    cur.close()
    conn.close()


def check_document_exists(key: str) -> bool:
    """
    Check if the document already exists in the database.

    Args:
        key (str): The key of the document.

    Returns:
        bool: True if the document exists, False otherwise.
    """
    # Connect to the PostgreSQL database
    conn = connect(DATABASE_URL)
    register_vector(conn)

    # Create a cursor object
    cur = conn.cursor()

    # Check if the document exists in the database
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM documents WHERE key = %s
        );
        """,
        (key,),
    )
    exists = cur.fetchone()[0]

    # Close the connection
    cur.close()
    conn.close()

    return exists


def generate_key(content: str) -> str:
    """
    Generate a unique key for the document based on its content.

    Args:
        content (str): The content of the document.

    Returns:
        str: A unique key for the document.
    """
    # Create an MD5 hash object
    md5_hash = hashlib.md5(content.encode("utf-8"))

    # Get the hexadecimal digest of the hash
    return f"doc-{md5_hash.hexdigest()}"


async def sync_to_permit(key: str, metadata: dict):
    """
    Synchronize the document with Permit.io.

    Args:
        key (str): The key of the document.
        metadata (dict): The metadata of the document.
    """
    # Initialize Permit
    permit = Permit(token=PERMIT_API_KEY, pdp=PERMT_PDP_URL)

    sensitivity = metadata.get("sensitivity", "low")

    resource_instance_data = {
        "key": key,
        "resource": "document",
        "tenant": "default",
        "attributes": {
            "sensitivity": sensitivity,
        },
    }

    # Sync document with Permit.io
    await permit.api.resource_instances.create(resource_instance_data)


async def process_document(file_path: str):
    with open(file_path, "r", encoding="utf-8") as file:
        doc = frontmatter.load(file)

    # Extract the content and metadata
    metadata = dict(doc.metadata)
    content = doc.content

    # Generate a unique key for the document
    key = generate_key(content)
    logger.info(f"Generated key for {file_path}: {key}")

    # Check if the document already exists in the database
    doc_exists = check_document_exists(key)
    if doc_exists:
        logger.info(f"Document {file_path} already exists in the database. Skipping.")
        return

    # Generate the embedding
    embedding = generate_embedding(content)
    logger.info(f"Generated embedding for {file_path}")

    # Insert the document into the database
    insert_document_to_db(
        content=content,
        title=metadata.get("title", "Untitled"),
        key=key,
        embedding=embedding,
    )

    # Synchronize with Permit.io
    await sync_to_permit(key, metadata)
    logger.info(f"Document {file_path} processed and synced with Permit.io")


async def process_documents():
    """
    Process all documents by adding them to the database,
    generating their embeddings, storing them in the database and
    synchronizing with Permit.io
    """
    # Get all the markdown files in the DOCS_DIR directory
    markdown_files = glob.glob(os.path.join(DOCS_DIR, "**", "*.md"), recursive=True)

    # Process each markdown file
    for file_path in markdown_files:
        await process_document(file_path)


if __name__ == "__main__":
    asyncio.run(process_documents())

import os
import logging

from dotenv import load_dotenv
from psycopg import connect
from pgvector.psycopg import register_vector

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Setting up the database...")

    # Connect to the PostgreSQL database
    conn = connect(DATABASE_URL)

    # Register the pgvector extension
    register_vector(conn)

    # Create a cursor object
    cur = conn.cursor()

    # Create the table with a vector column
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            content TEXT,
            title TEXT,
            key TEXT,
            sensitivity TEXT,
            embedding VECTOR(1536)
        );
    """)
    logger.info("Table 'documents' created successfully.")

    # Commit the changes and close the connection
    conn.commit()
    cur.close()
    conn.close()

#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Use the standard POSTGRES_USER variable provided by the official image
# Defaults to 'postgres' if not set, but it normally is.
PG_USER="${POSTGRES_USER:-postgres}"

echo "--- Initializing database 'sentinel_db' and enabling extension 'pgvector' ---"

# Check if the database already exists
# psql -tAc command checks for the database and outputs '1' if found, nothing otherwise
DB_EXISTS=$(psql -U "$PG_USER" -tAc "SELECT 1 FROM pg_database WHERE datname='sentinel_db'")

if [ "$DB_EXISTS" = '1' ]; then
    echo "Database 'sentinel_db' already exists. Skipping creation."
else
    echo "Database 'sentinel_db' does not exist. Creating..."
    # Create the database
    createdb -U "$PG_USER" "sentinel_db"
    echo "Database 'sentinel_db' created."
fi

# Connect to the specific database and enable the extension if it doesn't exist
echo "Ensuring extension pgvector is enabled in database 'sentinel_db'..."
psql -v ON_ERROR_STOP=1 --username "$PG_USER" --dbname "sentinel_db" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector CASCADE;
EOSQL

echo "--- Database initialization complete ---"
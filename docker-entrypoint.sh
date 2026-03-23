#!/bin/bash
set -e

echo "Starting moviedb-manager..."

# Function to wait for database
wait_for_db() {
    echo "Waiting for database to be ready..."
    # Simple check using python
    python << END
import asyncio
import asyncpg
import os
import time
import sys

async def check_db():
    host = os.getenv('MOVIEDB_DATABASE__HOST', 'db')
    port = int(os.getenv('MOVIEDB_DATABASE__PORT', 5432))
    user = os.getenv('MOVIEDB_DATABASE__USER', 'moviedb')
    password = os.getenv('MOVIEDB_DATABASE__PASSWORD', 'moviedb')
    database = os.getenv('MOVIEDB_DATABASE__NAME', 'moviedb')

    max_attempts = 30
    attempt = 0
    while attempt < max_attempts:
        try:
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                timeout=5
            )
            await conn.close()
            print("Database is ready!")
            return True
        except Exception as e:
            attempt += 1
            print(f"Database not ready (attempt {attempt}/{max_attempts}): {e}")
            time.sleep(1)
    return False

if __name__ == "__main__":
    result = asyncio.run(check_db())
    sys.exit(0 if result else 1)
END
}

# Wait for DB
wait_for_db

# Run migrations
if [ -d "alembic" ] && [ -f "alembic.ini" ]; then
    echo "Running migrations..."
    alembic upgrade head
fi

# Execute CMD
exec "$@"

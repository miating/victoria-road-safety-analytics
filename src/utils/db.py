"""Database connection helpers. Credentials come only from environment variables (.env)."""

import os

import psycopg
from dotenv import load_dotenv

REQUIRED_SETTINGS = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]


def connection_settings() -> dict:
    load_dotenv()
    missing = [name for name in REQUIRED_SETTINGS if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing database settings in .env: {', '.join(missing)}")
    return {
        "host": os.environ["DB_HOST"],
        "port": os.environ["DB_PORT"],
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "sslmode": os.getenv("DB_SSLMODE", "prefer"),
    }


def get_connection() -> psycopg.Connection:
    return psycopg.connect(**connection_settings())

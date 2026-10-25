"""Validate PostgreSQL configuration without opening a database connection."""
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def database_url(value):
    if not value or not value.strip():
        raise RuntimeError('DATABASE_URL is required. Set a PostgreSQL URL or pass -DatabaseUrl to start-backend.ps1.')
    try:
        url = make_url(value.strip())
    except (ArgumentError, ValueError):
        raise RuntimeError('Invalid DATABASE_URL. Expected postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE.') from None
    if url.drivername not in ('postgres', 'postgresql', 'postgresql+psycopg'):
        raise RuntimeError('Only PostgreSQL with the psycopg driver is supported.')
    if not url.database:
        raise RuntimeError('DATABASE_URL must include the PostgreSQL database name.')
    return url.set(drivername='postgresql+psycopg')

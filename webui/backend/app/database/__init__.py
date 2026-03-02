"""
Database Adapter Package
Provides abstraction layer for database operations (File-Based for Dev, PostgreSQL for Prod)
"""

from .adapter import DatabaseAdapter, get_database
from .file_database import FileDatabase
from .postgresql_database import PostgreSQLDatabase

__all__ = [
    "DatabaseAdapter",
    "get_database",
    "FileDatabase",
    "PostgreSQLDatabase",
]

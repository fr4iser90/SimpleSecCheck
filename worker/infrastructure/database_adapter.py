"""
Database adapter for the worker domain.

Provides database connection and session management for worker operations.
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool


class PostgreSQLAdapter:
    """Database adapter for worker operations."""
    
    def __init__(self, database_url: str):
        """Initialize the database adapter.
        
        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.engine = None
        self.async_session = None
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.WARNING)  # Suppress INFO logs from this module
    
    async def initialize(self) -> None:
        """Initialize the database connection."""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                poolclass=NullPool,
                future=True
            )
            
            # Create async session factory
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
        except Exception as e:
            self.logger.error(f"Error initializing database adapter: {e}")
            raise
    
    async def dispose(self) -> None:
        """Dispose the database connection."""
        try:
            if self.engine:
                await self.engine.dispose()
                
        except Exception as e:
            self.logger.error(f"Error disposing database adapter: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session.
        
        Yields:
            Database session
        """
        if not self.async_session:
            raise RuntimeError("Database adapter not initialized")
        
        session = self.async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
    
    async def test_connection(self) -> bool:
        """Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            return False
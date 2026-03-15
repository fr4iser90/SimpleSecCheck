"""
Database Adapter

This module provides the database adapter interface and implementation for the refactored backend.
It handles database connections, migrations, and health checks.
"""
from typing import Optional, List, Dict, Any
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, select
from sqlalchemy.exc import SQLAlchemyError
import logging

from config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class DatabaseAdapter:
    """Database adapter for PostgreSQL with async support."""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        
    async def init_database(self):
        """Initialize database connection and create tables."""
        try:
            # Normalize DATABASE_URL to use asyncpg driver
            database_url = settings.DATABASE_URL
            if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
            # Create async engine
            self.engine = create_async_engine(
                database_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            # Create session factory
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            await self.test_connection()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            async with self.async_session() as session:
                await session.execute(text("SELECT 1"))
                await session.commit()
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if not self.async_session:
            await self.init_database()
        return self.async_session()
    
    async def ensure_initialized(self):
        """Ensure database is initialized before use."""
        if not self.async_session:
            await self.init_database()
    
    async def close_database(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    async def get_health(self) -> Dict[str, Any]:
        """Get database health status."""
        try:
            is_healthy = await self.test_connection()
            return {
                "status": is_healthy,
                "type": "postgresql",
                "connection_string": settings.DATABASE_URL.split('@')[-1],  # Hide credentials
                "pool_size": settings.DATABASE_POOL_SIZE,
            }
        except Exception as e:
            return {
                "status": False,
                "type": "postgresql",
                "error": str(e),
            }
    
    async def check_table_exists(self, table_name: str) -> bool:
        """Check if a specific table exists in the database."""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    text("SELECT to_regclass(:table_name)"),
                    {"table_name": f"public.{table_name}"}
                )
                table_exists = result.scalar() is not None
                return table_exists
        except Exception as e:
            logger.error(f"Failed to check table existence for {table_name}: {e}")
            return False
    
    async def check_tables_exist(self) -> Dict[str, bool]:
        """Check if all required tables exist."""
        tables_to_check = ["users", "system_state", "scans", "vulnerabilities", "scanners"]
        results = {}
        
        for table in tables_to_check:
            results[table] = await self.check_table_exists(table)
        
        return results
    
    async def create_tables(self):
        """Create all database tables."""
        try:
            from infrastructure.database.models import Base
            
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Run migrations for existing tables
            await self._migrate_existing_tables()
            
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def _migrate_existing_tables(self):
        """Apply migrations to existing tables."""
        try:
            async with self.async_session() as session:
                # List of columns to check and add if missing
                columns_to_add = [
                    ("scheduled_at", "TIMESTAMP WITHOUT TIME ZONE"),
                    ("total_vulnerabilities", "INTEGER DEFAULT 0 NOT NULL"),
                    ("critical_vulnerabilities", "INTEGER DEFAULT 0 NOT NULL"),
                    ("high_vulnerabilities", "INTEGER DEFAULT 0 NOT NULL"),
                    ("medium_vulnerabilities", "INTEGER DEFAULT 0 NOT NULL"),
                    ("low_vulnerabilities", "INTEGER DEFAULT 0 NOT NULL"),
                    ("info_vulnerabilities", "INTEGER DEFAULT 0 NOT NULL"),
                ]
                
                for column_name, column_type in columns_to_add:
                    # Check if column exists
                    result = await session.execute(
                        text("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'scans' AND column_name = :column_name
                        """),
                        {"column_name": column_name}
                    )
                    column_exists = result.scalar() is not None
                    
                    if not column_exists:
                        logger.info(f"Adding {column_name} column to scans table")
                        await session.execute(
                            text(f"ALTER TABLE scans ADD COLUMN {column_name} {column_type}")
                        )
                        await session.commit()
                        logger.info(f"Successfully added {column_name} column")
                    else:
                        logger.debug(f"Column {column_name} already exists")
                
                # Migrate old vulnerabilities_count to total_vulnerabilities if needed
                result = await session.execute(
                    text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'scans' AND column_name = 'vulnerabilities_count'
                    """)
                )
                old_column_exists = result.scalar() is not None
                
                if old_column_exists:
                    logger.info("Migrating vulnerabilities_count to total_vulnerabilities")
                    # Copy data from old column to new column if total_vulnerabilities is 0
                    await session.execute(
                        text("""
                            UPDATE scans 
                            SET total_vulnerabilities = vulnerabilities_count 
                            WHERE total_vulnerabilities = 0 AND vulnerabilities_count IS NOT NULL
                        """)
                    )
                    # Drop the old column
                    await session.execute(
                        text("ALTER TABLE scans DROP COLUMN vulnerabilities_count")
                    )
                    await session.commit()
                    logger.info("Successfully migrated and removed vulnerabilities_count column")
                
                # Migrate old scan_type values to new ScanType enum values
                logger.info("Migrating scan_type values to new enum")
                scan_type_migrations = [
                    ("repository", "code"),
                    ("web_application", "website"),
                    ("infrastructure", "network"),
                    ("mobile_app", "mobile"),
                ]
                
                for old_value, new_value in scan_type_migrations:
                    result = await session.execute(
                        text("""
                            UPDATE scans 
                            SET scan_type = :new_value 
                            WHERE scan_type = :old_value
                        """),
                        {"old_value": old_value, "new_value": new_value}
                    )
                    updated_count = result.rowcount
                    if updated_count > 0:
                        logger.info(f"Migrated {updated_count} scans from scan_type '{old_value}' to '{new_value}'")
                
                await session.commit()
                logger.info("Successfully migrated scan_type values")
                        
        except Exception as e:
            logger.warning(f"Migration check failed (this is OK if tables don't exist yet): {e}")
            # Don't raise - migrations are optional
    
    async def check_admin_user_exists(self) -> bool:
        """Check if an admin user exists in the database."""
        try:
            # First check if table exists
            if not await self.check_table_exists("users"):
                return False
            
            async with self.async_session() as session:
                # Use SQLAlchemy ORM query with enum directly
                from infrastructure.database.models import User, UserRoleEnum
                result = await session.execute(
                    select(User).where(
                        User.role == UserRoleEnum.ADMIN,
                        User.is_active == True
                    )
                )
                admin_users = result.scalars().all()
                admin_count = len(admin_users) if admin_users else 0
                return admin_count > 0
        except Exception as e:
            # Only log if it's not a "table does not exist" error
            if "does not exist" not in str(e) and "relation" not in str(e).lower():
                logger.error(f"Failed to check admin user existence: {e}")
            return False
    
    async def check_system_state_exists(self) -> bool:
        """Check if system state record exists."""
        try:
            # First check if table exists
            if not await self.check_table_exists("system_state"):
                return False
            
            async with self.async_session() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM system_state")
                )
                state_count = result.scalar()
                return state_count > 0
        except Exception as e:
            # Only log if it's not a "table does not exist" error
            if "does not exist" not in str(e) and "relation" not in str(e).lower():
                logger.error(f"Failed to check system state existence: {e}")
            return False
    
    async def get_setup_status(self) -> Dict[str, Any]:
        """Get comprehensive setup status."""
        try:
            # Check table existence
            tables_exist = await self.check_tables_exist()
            
            # Check admin user
            admin_exists = await self.check_admin_user_exists()
            
            # Check system state
            system_state_exists = await self.check_system_state_exists()
            
            # Determine overall setup status
            # Check that tables_exist is not empty and all values are True
            # all([]) returns True in Python, so we need to check if dict is not empty first
            all_tables_exist = len(tables_exist) > 0 and all(tables_exist.values())
            setup_complete = (
                all_tables_exist and
                admin_exists and
                system_state_exists
            )
            
            return {
                "setup_complete": setup_complete,
                "tables": tables_exist,
                "admin_user_exists": admin_exists,
                "system_state_exists": system_state_exists,
                "database_connected": await self.test_connection(),
            }
        except Exception as e:
            logger.error(f"Failed to get setup status: {e}")
            return {
                "setup_complete": False,
                "tables": {},
                "admin_user_exists": False,
                "system_state_exists": False,
                "database_connected": False,
                "error": str(e),
            }


# Global database adapter instance
db_adapter = DatabaseAdapter()


async def init_database():
    """Initialize database for the application."""
    await db_adapter.init_database()


async def close_database():
    """Close database connections."""
    await db_adapter.close_database()


async def get_database_health() -> Dict[str, Any]:
    """Get database health status."""
    return await db_adapter.get_health()


async def check_setup_status() -> Dict[str, Any]:
    """Get comprehensive setup status."""
    return await db_adapter.get_setup_status()

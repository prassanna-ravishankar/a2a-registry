"""Database connection and utilities"""

import asyncpg

from .config import settings


class Database:
    """Database connection pool manager"""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Create database connection pool"""

        async def _init_connection(conn):
            # Set statement timeout to prevent runaway queries from holding connections
            timeout_ms = settings.database_statement_timeout_ms
            if timeout_ms > 0:
                await conn.execute(f"SET statement_timeout = {timeout_ms}")

        self.pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.database_pool_min_size,
            max_size=settings.database_pool_max_size,
            init=_init_connection,
        )

    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    async def execute(self, query: str, *args):
        """Execute a query that doesn't return results"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Fetch multiple rows"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Fetch a single row"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Fetch a single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)


# Global database instance
db = Database()


async def get_db():
    """Dependency injection for database access"""
    return db

"""
PostgreSQL Database Connection and Pool Manager
================================================
Manages PostgreSQL connection pool for mcp_smoke schema operations
"""

import logging
import asyncpg
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabasePool:
    """PostgreSQL connection pool manager"""
    
    def __init__(self, config):
        """
        Initialize database pool manager
        
        Args:
            config: Config instance with database settings
        """
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self):
        """Create connection pool"""
        try:
            db_config = {
                'host': self.config.get('database.host', 'localhost'),
                'port': self.config.get('database.port', 5436),
                'database': self.config.get('database.name', 'mcp'),
                'user': self.config.get('database.user', 'mcp'),
                'password': self.config.get('database.password', 'mcp'),
                'min_size': 2,
                'max_size': self.config.get('database.pool_size', 10),
                'command_timeout': 60,
            }
            
            self.pool = await asyncpg.create_pool(**db_config)
            
            # Test connection and set search path
            async with self.pool.acquire() as conn:
                schema = self.config.get('database.schema', 'mcp_smoke')
                await conn.execute(f'SET search_path TO {schema}, public')
                version = await conn.fetchval('SELECT version()')
                logger.info(f"✅ Database connection established: {version[:50]}...")
                logger.info(f"   Schema: {schema}")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Database pool closed")
    
    @asynccontextmanager
    async def acquire(self):
        """
        Acquire connection from pool
        
        Usage:
            async with db_pool.acquire() as conn:
                result = await conn.fetch('SELECT * FROM test_sessions')
        """
        async with self.pool.acquire() as conn:
            # Set search path for this connection
            schema = self.config.get('database.schema', 'mcp_smoke')
            await conn.execute(f'SET search_path TO {schema}, public')
            yield conn
    
    async def health_check(self) -> bool:
        """Check if database is healthy"""
        try:
            async with self.acquire() as conn:
                await conn.fetchval('SELECT 1')
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Singleton instance
_db_pool: Optional[DatabasePool] = None


async def get_db_pool(config) -> DatabasePool:
    """Get or create singleton database pool"""
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool(config)
        await _db_pool.initialize()
    return _db_pool


async def close_db_pool():
    """Close singleton database pool"""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None

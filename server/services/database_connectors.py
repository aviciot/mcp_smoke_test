# server/services/database_connectors.py
"""
Database Connectors
===================
Connection management for Oracle, MySQL, and PostgreSQL databases
"""

import oracledb
import aiomysql
import asyncpg
from typing import Optional, Dict, Any
import logging
from contextlib import asynccontextmanager
from server.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""
    pass


class OracleConnector:
    """Oracle database connector using python-oracledb"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Oracle connector
        
        Args:
            config: Database configuration dict with keys:
                - host: Database host
                - port: Database port (default: 1521)
                - service_name: Oracle service name
                - user: Username
                - password: Password
        """
        self.host = config['host']
        self.port = config.get('port', 1521)
        self.service_name = config['service_name']
        self.user = config['user']
        self.password = config['password']
        self._pool: Optional[oracledb.ConnectionPool] = None
    
    async def initialize(self):
        """Initialize connection pool"""
        try:
            # Create DSN
            dsn = f"{self.host}:{self.port}/{self.service_name}"
            
            # Create connection pool (synchronous API)
            self._pool = oracledb.create_pool(
                user=self.user,
                password=self.password,
                dsn=dsn,
                min=2,
                max=10,
                increment=1
            )
            
            logger.info(f"Oracle pool initialized: {self.host}/{self.service_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Oracle pool: {e}")
            raise DatabaseConnectionError(f"Oracle connection failed: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool"""
        if not self._pool:
            await self.initialize()
        
        conn = None
        try:
            # Get connection from pool (synchronous)
            conn = self._pool.acquire()
            yield conn
        except Exception as e:
            logger.error(f"Oracle connection error: {e}")
            raise DatabaseConnectionError(f"Oracle connection error: {e}")
        finally:
            if conn:
                self._pool.release(conn)
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> list[Dict]:
        """
        Execute SELECT query and return results as list of dicts
        
        Args:
            query: SQL query (must be SELECT)
            params: Optional query parameters
        
        Returns:
            List of row dictionaries
        """
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Get column names
                columns = [col[0].lower() for col in cursor.description]
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                # Convert to list of dicts
                return [dict(zip(columns, row)) for row in rows]
            finally:
                cursor.close()
    
    async def get_explain_plan(self, query: str) -> Dict[str, Any]:
        """
        Get execution plan for query
        
        Args:
            query: SQL query to analyze
        
        Returns:
            Dict with cost and plan details
        """
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Generate unique statement ID
                statement_id = f"STMT_{id(query)}"
                
                # Delete old plan
                cursor.execute(f"DELETE FROM plan_table WHERE statement_id = :sid", {'sid': statement_id})
                
                # Explain plan
                cursor.execute(f"EXPLAIN PLAN SET STATEMENT_ID = :sid FOR {query}", {'sid': statement_id})
                
                # Get plan details
                cursor.execute("""
                    SELECT cost, cardinality, bytes
                    FROM plan_table
                    WHERE statement_id = :sid
                    AND parent_id IS NULL
                """, {'sid': statement_id})
                
                row = cursor.fetchone()
                
                # Clean up
                cursor.execute(f"DELETE FROM plan_table WHERE statement_id = :sid", {'sid': statement_id})
                
                if row:
                    return {
                        'cost': row[0] or 0,
                        'cardinality': row[1] or 0,
                        'bytes': row[2] or 0
                    }
                else:
                    return {'cost': 0, 'cardinality': 0, 'bytes': 0}
            finally:
                cursor.close()
    
    async def close(self):
        """Close connection pool"""
        if self._pool:
            self._pool.close()
            self._pool = None


class MySQLConnector:
    """MySQL database connector using aiomysql"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MySQL connector
        
        Args:
            config: Database configuration dict with keys:
                - host: Database host
                - port: Database port (default: 3306)
                - database: Database name
                - user: Username
                - password: Password
        """
        self.host = config['host']
        self.port = config.get('port', 3306)
        self.database = config['database']
        self.user = config['user']
        self.password = config['password']
        self._pool: Optional[aiomysql.Pool] = None
    
    async def initialize(self):
        """Initialize connection pool"""
        try:
            self._pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                minsize=2,
                maxsize=10,
                autocommit=True
            )
            
            logger.info(f"MySQL pool initialized: {self.host}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to initialize MySQL pool: {e}")
            raise DatabaseConnectionError(f"MySQL connection failed: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool"""
        if not self._pool:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> list[Dict]:
        """
        Execute SELECT query and return results as list of dicts
        
        Args:
            query: SQL query (must be SELECT)
            params: Optional query parameters
        
        Returns:
            List of row dictionaries
        """
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if params:
                    await cursor.execute(query, params)
                else:
                    await cursor.execute(query)
                
                rows = await cursor.fetchall()
                return list(rows)
    
    async def get_explain_plan(self, query: str) -> Dict[str, Any]:
        """
        Get execution plan for query
        
        Args:
            query: SQL query to analyze
        
        Returns:
            Dict with cost and plan details
        """
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # Get EXPLAIN output
                await cursor.execute(f"EXPLAIN {query}")
                rows = await cursor.fetchall()
                
                if rows:
                    # Sum up row estimates as a rough cost proxy
                    total_rows = sum(row.get('rows', 0) or 0 for row in rows)
                    return {
                        'cost': total_rows,  # MySQL doesn't have cost, use row count
                        'cardinality': total_rows,
                        'rows': total_rows
                    }
                else:
                    return {'cost': 0, 'cardinality': 0, 'rows': 0}
    
    async def close(self):
        """Close connection pool"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None


class PostgreSQLConnector:
    """PostgreSQL database connector using asyncpg"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PostgreSQL connector
        
        Args:
            config: Database configuration dict with keys:
                - host: Database host
                - port: Database port (default: 5432)
                - database: Database name
                - user: Username
                - password: Password
        """
        self.host = config['host']
        self.port = config.get('port', 5432)
        self.database = config['database']
        self.user = config['user']
        self.password = config['password']
        self._pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize connection pool"""
        try:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=2,
                max_size=10
            )
            
            logger.info(f"PostgreSQL pool initialized: {self.host}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise DatabaseConnectionError(f"PostgreSQL connection failed: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool"""
        if not self._pool:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> list[Dict]:
        """
        Execute SELECT query and return results as list of dicts
        
        Args:
            query: SQL query (must be SELECT)
            params: Optional query parameters
        
        Returns:
            List of row dictionaries
        """
        async with self.get_connection() as conn:
            if params:
                rows = await conn.fetch(query, *params)
            else:
                rows = await conn.fetch(query)
            
            # Convert Record objects to dicts
            return [dict(row) for row in rows]
    
    async def get_explain_plan(self, query: str) -> Dict[str, Any]:
        """
        Get execution plan for query
        
        Args:
            query: SQL query to analyze
        
        Returns:
            Dict with cost and plan details
        """
        async with self.get_connection() as conn:
            # Get EXPLAIN (FORMAT JSON) output
            result = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {query}")
            
            if result and len(result) > 0:
                plan = result[0].get('Plan', {})
                return {
                    'cost': plan.get('Total Cost', 0),
                    'startup_cost': plan.get('Startup Cost', 0),
                    'rows': plan.get('Plan Rows', 0)
                }
            else:
                return {'cost': 0, 'startup_cost': 0, 'rows': 0}
    
    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None


class DatabaseConnectorFactory:
    """Factory for creating database connectors"""
    
    _connectors: Dict[str, Any] = {}
    
    @classmethod
    async def get_connector(cls, database_name: str):
        """
        Get or create a connector for the specified database
        
        Args:
            database_name: Name of database from settings.yaml
        
        Returns:
            Database connector instance
        
        Raises:
            DatabaseConnectionError: If database not found or connection fails
        """
        # Check cache
        if database_name in cls._connectors:
            return cls._connectors[database_name]
        
        # Get settings
        settings = get_settings()
        
        if not hasattr(settings, 'comparison_databases'):
            raise DatabaseConnectionError("No comparison_databases configured")
        
        if database_name not in settings.comparison_databases:
            available = list(settings.comparison_databases.keys())
            raise DatabaseConnectionError(
                f"Database '{database_name}' not found. Available: {available}"
            )
        
        config = settings.comparison_databases[database_name]
        db_type = config.get('type', '').lower()
        
        # Create appropriate connector
        if db_type == 'oracle':
            connector = OracleConnector(config)
        elif db_type == 'mysql':
            connector = MySQLConnector(config)
        elif db_type == 'postgresql':
            connector = PostgreSQLConnector(config)
        else:
            raise DatabaseConnectionError(f"Unsupported database type: {db_type}")
        
        # Initialize
        await connector.initialize()
        
        # Cache
        cls._connectors[database_name] = connector
        
        return connector
    
    @classmethod
    async def close_all(cls):
        """Close all cached connectors"""
        for connector in cls._connectors.values():
            await connector.close()
        cls._connectors.clear()

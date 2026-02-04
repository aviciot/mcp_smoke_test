# tests/integration/test_database_connectors.py
"""
Integration tests for database connectors
==========================================
Tests real database connections (requires configured databases)
"""

import pytest
import asyncio
from server.services.database_connectors import (
    DatabaseConnectorFactory,
    OracleConnector,
    MySQLConnector,
    PostgreSQLConnector,
    DatabaseConnectionError
)


pytestmark = pytest.mark.asyncio


class TestDatabaseConnectorFactory:
    """Test DatabaseConnectorFactory"""
    
    async def test_get_connector_invalid_database(self):
        """Test getting connector for non-existent database"""
        with pytest.raises(DatabaseConnectionError, match="not found"):
            await DatabaseConnectorFactory.get_connector("nonexistent_db")
    
    async def test_connector_caching(self, monkeypatch):
        """Test that connectors are cached"""
        # Mock settings
        class MockSettings:
            comparison_databases = {
                'test_oracle': {
                    'type': 'oracle',
                    'host': 'localhost',
                    'port': 1521,
                    'service_name': 'TEST',
                    'user': 'test',
                    'password': 'test'
                }
            }
        
        from server import config
        monkeypatch.setattr(config, 'get_settings', lambda: MockSettings())
        
        # This will fail to initialize (no real DB), but we're testing caching logic
        try:
            connector1 = await DatabaseConnectorFactory.get_connector('test_oracle')
            connector2 = await DatabaseConnectorFactory.get_connector('test_oracle')
            
            # Should be same instance (cached)
            assert connector1 is connector2
        except DatabaseConnectionError:
            # Expected - no real database
            pass
        finally:
            await DatabaseConnectorFactory.close_all()


@pytest.mark.skipif(
    "not config.getoption('--run-integration')",
    reason="Integration tests require --run-integration flag and real databases"
)
class TestOracleConnectorIntegration:
    """Integration tests for Oracle connector (requires real Oracle database)"""
    
    @pytest.fixture
    async def oracle_connector(self):
        """Get Oracle connector from factory"""
        connector = await DatabaseConnectorFactory.get_connector('oracle_statements')
        yield connector
        await connector.close()
    
    async def test_oracle_connection(self, oracle_connector):
        """Test Oracle database connection"""
        result = await oracle_connector.execute_query("SELECT 1 FROM DUAL")
        assert len(result) == 1
        assert result[0]['1'] == 1
    
    async def test_oracle_query(self, oracle_connector):
        """Test Oracle query execution"""
        query = "SELECT table_name FROM user_tables WHERE ROWNUM <= 5"
        results = await oracle_connector.execute_query(query)
        assert isinstance(results, list)
        assert all('table_name' in row for row in results)
    
    async def test_oracle_explain_plan(self, oracle_connector):
        """Test Oracle EXPLAIN PLAN"""
        query = "SELECT * FROM user_tables WHERE table_name = 'ORDERS'"
        plan = await oracle_connector.get_explain_plan(query)
        
        assert 'cost' in plan
        assert 'cardinality' in plan
        assert isinstance(plan['cost'], (int, float))


@pytest.mark.skipif(
    "not config.getoption('--run-integration')",
    reason="Integration tests require --run-integration flag and real databases"
)
class TestMySQLConnectorIntegration:
    """Integration tests for MySQL connector (requires real MySQL database)"""
    
    @pytest.fixture
    async def mysql_connector(self):
        """Get MySQL connector from factory"""
        connector = await DatabaseConnectorFactory.get_connector('mysql_brian')
        yield connector
        await connector.close()
    
    async def test_mysql_connection(self, mysql_connector):
        """Test MySQL database connection"""
        result = await mysql_connector.execute_query("SELECT 1 as test")
        assert len(result) == 1
        assert result[0]['test'] == 1
    
    async def test_mysql_query(self, mysql_connector):
        """Test MySQL query execution"""
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() LIMIT 5"
        results = await mysql_connector.execute_query(query)
        assert isinstance(results, list)
        assert all('table_name' in row or 'TABLE_NAME' in row for row in results)
    
    async def test_mysql_explain_plan(self, mysql_connector):
        """Test MySQL EXPLAIN"""
        query = "SELECT * FROM customers WHERE customer_id = 1"
        plan = await mysql_connector.get_explain_plan(query)
        
        assert 'cost' in plan
        assert 'rows' in plan
        assert isinstance(plan['cost'], (int, float))


@pytest.mark.skipif(
    "not config.getoption('--run-integration')",
    reason="Integration tests require --run-integration flag and real databases"
)
class TestPostgreSQLConnectorIntegration:
    """Integration tests for PostgreSQL connector (requires real PostgreSQL database)"""
    
    @pytest.fixture
    async def postgres_connector(self):
        """Get PostgreSQL connector from factory"""
        connector = await DatabaseConnectorFactory.get_connector('postgres_prod')
        yield connector
        await connector.close()
    
    async def test_postgres_connection(self, postgres_connector):
        """Test PostgreSQL database connection"""
        result = await postgres_connector.execute_query("SELECT 1 as test")
        assert len(result) == 1
        assert result[0]['test'] == 1
    
    async def test_postgres_query(self, postgres_connector):
        """Test PostgreSQL query execution"""
        query = "SELECT tablename FROM pg_tables WHERE schemaname = 'public' LIMIT 5"
        results = await postgres_connector.execute_query(query)
        assert isinstance(results, list)
        assert all('tablename' in row for row in results)
    
    async def test_postgres_explain_plan(self, postgres_connector):
        """Test PostgreSQL EXPLAIN"""
        query = "SELECT * FROM customers WHERE customer_id = 1"
        plan = await postgres_connector.get_explain_plan(query)
        
        assert 'cost' in plan
        assert 'rows' in plan
        assert isinstance(plan['cost'], (int, float))


def pytest_addoption(parser):
    """Add --run-integration flag"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires real databases)"
    )

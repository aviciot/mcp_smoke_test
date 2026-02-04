"""
Unit Tests for Execution Plan Analyzer
=======================================
Tests query cost estimation and plan analysis
"""

import pytest
from server.services.execution_plan_analyzer import (
    ExecutionPlanAnalyzer,
    PlanAnalysis,
    ExecutionCost
)


class TestExecutionPlanAnalyzer:
    """Test ExecutionPlanAnalyzer class"""
    
    @pytest.mark.asyncio
    async def test_oracle_low_cost_query(self):
        """Test Oracle query with low cost passes"""
        analyzer = ExecutionPlanAnalyzer()
        
        # Mock Oracle EXPLAIN output (low cost)
        oracle_plan = """
        Plan hash value: 123456789
        
        | Id | Operation         | Name  | Rows | Cost (%CPU)|
        |  0 | SELECT STATEMENT  |       |  100 |    5   (0) |
        |  1 | TABLE ACCESS FULL | USERS |  100 |    5   (0) |
        """
        
        async def mock_explain(query):
            return oracle_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM users LIMIT 100",
            'oracle',
            mock_explain
        )
        
        assert result.is_acceptable is True
        assert result.estimated_time_sec < 60
        assert result.cost_level in [ExecutionCost.LOW, ExecutionCost.MEDIUM]
    
    @pytest.mark.asyncio
    async def test_oracle_high_cost_blocked(self):
        """Test Oracle query with excessive cost is blocked"""
        analyzer = ExecutionPlanAnalyzer()
        
        # Mock Oracle EXPLAIN with very high cost
        oracle_plan = """
        Plan hash value: 987654321
        
        | Id | Operation         | Name   | Rows     | Cost (%CPU)|
        |  0 | SELECT STATEMENT  |        | 10000000 | 500000 (5) |
        |  1 | TABLE ACCESS FULL | ORDERS | 10000000 | 500000 (5) |
        """
        
        async def mock_explain(query):
            return oracle_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM orders",
            'oracle',
            mock_explain
        )
        
        assert result.is_acceptable is False
        assert result.estimated_time_sec > analyzer.MAX_EXECUTION_TIME_SEC
        assert result.cost_level == ExecutionCost.EXCESSIVE
    
    @pytest.mark.asyncio
    async def test_oracle_full_table_scan_warning(self):
        """Test Oracle full table scan generates warning"""
        analyzer = ExecutionPlanAnalyzer()
        
        oracle_plan = """
        | Id | Operation              | Name  | Rows | Cost |
        |  0 | SELECT STATEMENT       |       | 1000 |  50  |
        |  1 | TABLE ACCESS FULL      | USERS | 1000 |  50  |
        """
        
        async def mock_explain(query):
            return oracle_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM users",
            'oracle',
            mock_explain
        )
        
        assert result.has_full_table_scan is True
        assert any('Full table scan' in r for r in result.recommendations)
    
    @pytest.mark.asyncio
    async def test_oracle_cartesian_product_warning(self):
        """Test Oracle Cartesian product generates warning"""
        analyzer = ExecutionPlanAnalyzer()
        
        oracle_plan = """
        | Id | Operation              | Name    | Rows   | Cost   |
        |  0 | SELECT STATEMENT       |         | 100000 | 10000  |
        |  1 | MERGE JOIN CARTESIAN   |         | 100000 | 10000  |
        |  2 | TABLE ACCESS FULL      | USERS   | 1000   | 50     |
        |  3 | TABLE ACCESS FULL      | ORDERS  | 100    | 10     |
        """
        
        async def mock_explain(query):
            return oracle_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM users, orders",
            'oracle',
            mock_explain
        )
        
        assert any('Cartesian product' in r for r in result.recommendations)
    
    @pytest.mark.asyncio
    async def test_mysql_low_cost_query(self):
        """Test MySQL query with low cost passes"""
        analyzer = ExecutionPlanAnalyzer()
        
        # Mock MySQL EXPLAIN output
        mysql_plan = """
        id: 1
        select_type: SIMPLE
        table: users
        type: ref
        possible_keys: idx_status
        key: idx_status
        rows: 100
        Extra: Using where
        """
        
        async def mock_explain(query):
            return mysql_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM users WHERE status = 'active'",
            'mysql',
            mock_explain
        )
        
        assert result.is_acceptable is True
        assert result.estimated_rows == 100
        assert result.cost_level == ExecutionCost.LOW
    
    @pytest.mark.asyncio
    async def test_mysql_full_table_scan_warning(self):
        """Test MySQL full table scan generates warning"""
        analyzer = ExecutionPlanAnalyzer()
        
        mysql_plan = """
        id: 1
        select_type: SIMPLE
        table: orders
        type: ALL
        possible_keys: NULL
        key: NULL
        rows: 1000000
        Extra: Using where
        """
        
        async def mock_explain(query):
            return mysql_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM orders",
            'mysql',
            mock_explain
        )
        
        assert result.has_full_table_scan is True
        assert any('Full table scan' in r for r in result.recommendations)
    
    @pytest.mark.asyncio
    async def test_mysql_filesort_warning(self):
        """Test MySQL filesort generates warning"""
        analyzer = ExecutionPlanAnalyzer()
        
        mysql_plan = """
        id: 1
        select_type: SIMPLE
        table: users
        type: ALL
        rows: 10000
        Extra: Using filesort
        """
        
        async def mock_explain(query):
            return mysql_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM users ORDER BY created_at",
            'mysql',
            mock_explain
        )
        
        assert any('Filesort' in r for r in result.recommendations)
    
    @pytest.mark.asyncio
    async def test_mysql_temporary_table_warning(self):
        """Test MySQL temporary table generates warning"""
        analyzer = ExecutionPlanAnalyzer()
        
        mysql_plan = """
        id: 1
        select_type: SIMPLE
        table: users
        rows: 5000
        Extra: Using temporary
        """
        
        async def mock_explain(query):
            return mysql_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT DISTINCT * FROM users",
            'mysql',
            mock_explain
        )
        
        assert any('Temporary table' in r for r in result.recommendations)
    
    @pytest.mark.asyncio
    async def test_postgresql_low_cost_query(self):
        """Test PostgreSQL query with low cost passes"""
        analyzer = ExecutionPlanAnalyzer()
        
        # Mock PostgreSQL EXPLAIN JSON output
        pg_plan = """
        {
          "Plan": {
            "Node Type": "Index Scan",
            "Relation Name": "users",
            "Startup Cost": 0.42,
            "Total Cost": 8.44,
            "Plan Rows": 100,
            "Plan Width": 244
          }
        }
        """
        
        async def mock_explain(query):
            return pg_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM users WHERE id = 1",
            'postgresql',
            mock_explain
        )
        
        assert result.is_acceptable is True
        assert result.estimated_rows == 100
        assert result.cost_level == ExecutionCost.LOW
    
    @pytest.mark.asyncio
    async def test_postgresql_seq_scan_warning(self):
        """Test PostgreSQL sequential scan generates warning"""
        analyzer = ExecutionPlanAnalyzer()
        
        pg_plan = """
        {
          "Plan": {
            "Node Type": "Seq Scan",
            "Relation Name": "orders",
            "Startup Cost": 0.00,
            "Total Cost": 15000.00,
            "Plan Rows": 1000000,
            "Plan Width": 100
          }
        }
        """
        
        async def mock_explain(query):
            return pg_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM orders",
            'postgresql',
            mock_explain
        )
        
        assert result.has_full_table_scan is True
        assert any('Sequential scan' in r for r in result.recommendations)
    
    @pytest.mark.asyncio
    async def test_postgresql_high_row_count_warning(self):
        """Test PostgreSQL high row count generates warning"""
        analyzer = ExecutionPlanAnalyzer()
        
        pg_plan = """
        {
          "Plan": {
            "Node Type": "Index Scan",
            "Total Cost": 50000,
            "Plan Rows": 5000000
          }
        }
        """
        
        async def mock_explain(query):
            return pg_plan
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM big_table",
            'postgresql',
            mock_explain
        )
        
        assert any('High row count' in r for r in result.recommendations)
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Test analyzer statistics tracking"""
        analyzer = ExecutionPlanAnalyzer()
        
        # Low cost query
        async def mock_low_cost(query):
            return "Cost: 10, Rows: 100"
        
        # High cost query
        async def mock_high_cost(query):
            return "Cost: 5000000, Rows: 10000000"
        
        # Analyze multiple queries
        await analyzer.analyze_query_cost("SELECT 1", 'oracle', mock_low_cost)
        await analyzer.analyze_query_cost("SELECT 2", 'oracle', mock_high_cost)
        await analyzer.analyze_query_cost("SELECT 3", 'oracle', mock_low_cost)
        
        stats = analyzer.get_stats()
        
        assert stats['total_analyses'] == 3
        assert stats['blocked_queries'] == 1  # The high cost one
        assert 0 < stats['success_rate'] < 100
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test analyzer handles errors gracefully"""
        analyzer = ExecutionPlanAnalyzer()
        
        async def mock_error(query):
            raise Exception("Database connection lost")
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM users",
            'oracle',
            mock_error
        )
        
        assert result.is_acceptable is False
        assert result.error_message is not None
        assert 'Database connection lost' in result.error_message
    
    def test_cost_level_determination(self):
        """Test cost level classification"""
        analyzer = ExecutionPlanAnalyzer()
        
        # Test LOW
        assert analyzer._determine_cost_level(30) == ExecutionCost.LOW
        
        # Test MEDIUM
        assert analyzer._determine_cost_level(90) == ExecutionCost.MEDIUM
        
        # Test HIGH
        assert analyzer._determine_cost_level(200) == ExecutionCost.HIGH
        
        # Test EXCESSIVE
        assert analyzer._determine_cost_level(400) == ExecutionCost.EXCESSIVE
    
    @pytest.mark.asyncio
    async def test_unsupported_database_type(self):
        """Test unsupported database type raises error"""
        analyzer = ExecutionPlanAnalyzer()
        
        async def mock_explain(query):
            return "some plan"
        
        result = await analyzer.analyze_query_cost(
            "SELECT * FROM users",
            'mongodb',  # Not supported
            mock_explain
        )
        
        assert result.is_acceptable is False
        assert result.error_message is not None
    
    def test_to_dict_conversion(self):
        """Test PlanAnalysis to_dict conversion"""
        analysis = PlanAnalysis(
            is_acceptable=True,
            estimated_time_sec=45.5,
            estimated_rows=1000,
            estimated_cost=123.456,
            cost_level=ExecutionCost.MEDIUM,
            has_full_table_scan=False,
            recommendations=["Add index"],
            raw_plan="some plan"
        )
        
        result = analysis.to_dict()
        
        assert result['is_acceptable'] is True
        assert result['estimated_time_sec'] == 45.5
        assert result['estimated_rows'] == 1000
        assert result['estimated_cost'] == 123.46  # Rounded
        assert result['cost_level'] == 'medium'
        assert result['has_full_table_scan'] is False
        assert result['recommendations'] == ["Add index"]

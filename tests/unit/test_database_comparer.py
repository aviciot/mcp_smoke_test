"""
Unit Tests for Database Comparer
=================================
Tests in-database comparison with temp tables
"""

import pytest
from server.services.database_comparer import (
    DatabaseComparer,
    ComparisonConfig,
    ComparisonResult
)


class TestDatabaseComparer:
    """Test DatabaseComparer class"""
    
    @pytest.mark.asyncio
    async def test_identical_tables_postgresql(self):
        """Test comparison of identical tables in PostgreSQL"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id, name FROM users WHERE status = 'active'",
            target_query="SELECT id, name FROM users WHERE status = 'active'",
            key_columns=['id']
        )
        
        # Mock query execution
        query_results = {
            'CREATE': None,
            'SELECT COUNT': [[100]],  # 100 rows in both
            'stats': []  # No mismatches
        }
        
        async def mock_execute(query):
            if 'CREATE' in query:
                return query_results['CREATE']
            elif 'COUNT(*)' in query:
                return query_results['SELECT COUNT']
            elif 'GROUP BY' in query:
                return query_results['stats']
            return None
        
        result = await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute,
            session_id='test-123'
        )
        
        assert result.match_status == 'identical'
        assert result.total_rows_source == 100
        assert result.total_rows_target == 100
        assert result.matching_rows == 0  # No mismatches found
        assert result.missing_in_target == 0
        assert result.missing_in_source == 0
        assert result.comparison_time_sec > 0
    
    @pytest.mark.asyncio
    async def test_missing_rows_in_target(self):
        """Test detection of rows missing in target"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id, name FROM source_table",
            target_query="SELECT id, name FROM target_table",
            key_columns=['id']
        )
        
        # Mock: source has 150 rows, target has 100 rows, 50 missing
        query_results = {
            'CREATE': None,
            'count_calls': 0
        }
        
        async def mock_execute(query):
            if 'CREATE' in query:
                return query_results['CREATE']
            elif 'COUNT(*)' in query:
                query_results['count_calls'] += 1
                if query_results['count_calls'] == 1:
                    return [[150]]  # Source count
                else:
                    return [[100]]  # Target count
            elif 'GROUP BY' in query:
                # Return stats with mismatches
                return [['missing_in_target', 50]]
            return None
        
        result = await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute
        )
        
        assert result.match_status == 'mismatch'
        assert result.total_rows_source == 150
        assert result.total_rows_target == 100
        assert result.missing_in_target == 50
        assert result.missing_in_source == 0
    
    @pytest.mark.asyncio
    async def test_missing_rows_in_source(self):
        """Test detection of rows missing in source"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id, name FROM source_table",
            target_query="SELECT id, name FROM target_table",
            key_columns=['id']
        )
        
        # Mock: source has 80 rows, target has 100 rows, 20 missing in source
        query_results = {
            'CREATE': None,
            'count_calls': 0,
            'stats': [
                {'mismatch_type': 'missing_in_source', 'count': 20}
            ]
        }
        
        async def mock_execute(query):
            if 'CREATE' in query:
                return None
            elif 'COUNT(*)' in query:
                query_results['count_calls'] += 1
                if query_results['count_calls'] == 1:
                    return [[80]]  # Source
                else:
                    return [[100]]  # Target
            elif 'GROUP BY' in query:
                return query_results['stats']
            return None
        
        result = await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute
        )
        
        assert result.match_status == 'mismatch'
        assert result.missing_in_target == 0
        assert result.missing_in_source == 20
    
    @pytest.mark.asyncio
    async def test_value_mismatches(self):
        """Test detection of value mismatches"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id, name, email FROM users",
            target_query="SELECT id, name, email FROM users_backup",
            key_columns=['id'],
            compare_columns=['name', 'email']
        )
        
        query_results = {
            'CREATE': None,
            'count_calls': 0,
            'stats': [
                {'mismatch_type': 'value_mismatch', 'count': 15}
            ]
        }
        
        async def mock_execute(query):
            if 'CREATE' in query:
                return None
            elif 'COUNT(*)' in query:
                query_results['count_calls'] += 1
                return [[100]]  # Same count
            elif 'GROUP BY' in query:
                return query_results['stats']
            return None
        
        result = await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute
        )
        
        assert result.match_status == 'mismatch'
        assert result.mismatched_rows == 15
        assert result.total_rows_source == 100
        assert result.total_rows_target == 100
    
    @pytest.mark.asyncio
    async def test_multiple_key_columns(self):
        """Test comparison with composite key"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT year, month, revenue FROM sales",
            target_query="SELECT year, month, revenue FROM sales_backup",
            key_columns=['year', 'month']
        )
        
        query_results = {
            'CREATE': None,
            'count_calls': 0,
            'stats': []  # Identical
        }
        
        async def mock_execute(query):
            if 'CREATE' in query:
                return None
            elif 'COUNT(*)' in query:
                return [[1000]]
            elif 'GROUP BY' in query:
                return query_results['stats']
            return None
        
        result = await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute
        )
        
        assert result.match_status == 'identical'
        assert result.total_rows_source == 1000
    
    @pytest.mark.asyncio
    async def test_mysql_comparison(self):
        """Test MySQL-specific comparison (uses UNION instead of FULL OUTER JOIN)"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id, name FROM users",
            target_query="SELECT id, name FROM users_copy",
            key_columns=['id']
        )
        
        async def mock_execute(query):
            # Verify MySQL syntax
            if 'CREATE TEMPORARY TABLE' in query:
                assert 'UNION ALL' in query or 'AS' in query
                return None
            elif 'COUNT(*)' in query:
                return [[50]]
            elif 'GROUP BY' in query:
                return []
            return None
        
        result = await comparer.compare_tables(
            config,
            'mysql',
            mock_execute
        )
        
        assert result.match_status == 'identical'
    
    @pytest.mark.asyncio
    async def test_oracle_comparison(self):
        """Test Oracle-specific comparison (uses GLOBAL TEMPORARY TABLE)"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id, name FROM users",
            target_query="SELECT id, name FROM users_copy",
            key_columns=['id']
        )
        
        async def mock_execute(query):
            # Verify Oracle syntax
            if 'CREATE GLOBAL TEMPORARY TABLE' in query:
                assert 'ON COMMIT PRESERVE ROWS' in query
                return None
            elif 'COUNT(*)' in query:
                return [[75]]
            elif 'GROUP BY' in query:
                return []
            return None
        
        result = await comparer.compare_tables(
            config,
            'oracle',
            mock_execute
        )
        
        assert result.match_status == 'identical'
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling during comparison"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT * FROM nonexistent_table",
            target_query="SELECT * FROM another_table",
            key_columns=['id']
        )
        
        async def mock_execute(query):
            if 'CREATE' in query and 'nonexistent' in query:
                raise Exception("Table does not exist")
            return None
        
        result = await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute
        )
        
        assert result.match_status == 'error'
        assert result.error_message is not None
        assert 'Table does not exist' in result.error_message
        assert result.comparison_time_sec > 0
    
    @pytest.mark.asyncio
    async def test_temp_table_tracking(self):
        """Test temporary table tracking"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id FROM users",
            target_query="SELECT id FROM orders",
            key_columns=['id']
        )
        
        async def mock_execute(query):
            if 'COUNT(*)' in query:
                return [[10]]
            elif 'GROUP BY' in query:
                return []
            return None
        
        # Before comparison
        assert len(comparer.temp_tables_created) == 0
        
        await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute
        )
        
        # After comparison
        assert len(comparer.temp_tables_created) == 3  # source, target, mismatch
        
        stats = comparer.get_stats()
        assert stats['total_comparisons'] == 1
        assert stats['active_temp_tables'] == 3
    
    @pytest.mark.asyncio
    async def test_cleanup_temp_tables(self):
        """Test cleanup of temporary tables"""
        comparer = DatabaseComparer()
        
        # Add some fake temp tables
        comparer.temp_tables_created = [
            'tmp_src_123',
            'tmp_tgt_123',
            'tmp_mismatch_123'
        ]
        
        drop_queries = []
        
        async def mock_execute(query):
            if 'DROP' in query:
                drop_queries.append(query)
            return None
        
        await comparer.cleanup_temp_tables('postgresql', mock_execute)
        
        # Verify cleanup
        assert len(comparer.temp_tables_created) == 0
        assert len(drop_queries) == 3
        assert all('DROP TABLE' in q for q in drop_queries)
    
    @pytest.mark.asyncio
    async def test_cleanup_with_errors(self):
        """Test cleanup continues even if some drops fail"""
        comparer = DatabaseComparer()
        
        comparer.temp_tables_created = [
            'tmp_src_123',
            'tmp_tgt_456',
            'tmp_mismatch_789'
        ]
        
        drop_count = 0
        
        async def mock_execute(query):
            nonlocal drop_count
            if 'DROP' in query:
                drop_count += 1
                if 'tmp_tgt' in query:
                    raise Exception("Table already dropped")
            return None
        
        # Should not raise exception
        await comparer.cleanup_temp_tables('postgresql', mock_execute)
        
        # All drops attempted
        assert drop_count == 3
        # List cleared
        assert len(comparer.temp_tables_created) == 0
    
    @pytest.mark.asyncio
    async def test_dict_result_format(self):
        """Test result counts from dict format"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id FROM test",
            target_query="SELECT id FROM test",
            key_columns=['id']
        )
        
        async def mock_execute(query):
            if 'COUNT(*)' in query:
                # Return dict format (some drivers do this)
                return [{'count': 42}]
            elif 'GROUP BY' in query:
                return []
            return None
        
        result = await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute
        )
        
        assert result.total_rows_source == 42
        assert result.total_rows_target == 42
    
    @pytest.mark.asyncio
    async def test_tuple_result_format(self):
        """Test result counts from tuple format"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id FROM test",
            target_query="SELECT id FROM test",
            key_columns=['id']
        )
        
        async def mock_execute(query):
            if 'COUNT(*)' in query:
                # Return tuple format
                return [(100,)]
            elif 'GROUP BY' in query:
                return []
            return None
        
        result = await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute
        )
        
        assert result.total_rows_source == 100
        assert result.total_rows_target == 100
    
    @pytest.mark.asyncio
    async def test_mixed_mismatch_types(self):
        """Test comparison with multiple mismatch types"""
        comparer = DatabaseComparer()
        
        config = ComparisonConfig(
            source_query="SELECT id, value FROM test1",
            target_query="SELECT id, value FROM test2",
            key_columns=['id']
        )
        
        query_results = {
            'count_calls': 0,
            'stats': [
                {'mismatch_type': 'missing_in_target', 'count': 10},
                {'mismatch_type': 'missing_in_source', 'count': 5},
                {'mismatch_type': 'value_mismatch', 'count': 8}
            ]
        }
        
        async def mock_execute(query):
            if 'CREATE' in query:
                return None
            elif 'COUNT(*)' in query:
                query_results['count_calls'] += 1
                if query_results['count_calls'] == 1:
                    return [[110]]  # Source: 100 + 10 missing in target
                else:
                    return [[105]]  # Target: 100 + 5 missing in source
            elif 'GROUP BY' in query:
                return query_results['stats']
            return None
        
        result = await comparer.compare_tables(
            config,
            'postgresql',
            mock_execute
        )
        
        assert result.match_status == 'mismatch'
        assert result.missing_in_target == 10
        assert result.missing_in_source == 5
        assert result.mismatched_rows == 8
    
    def test_to_dict_conversion(self):
        """Test ComparisonResult to_dict conversion"""
        result = ComparisonResult(
            match_status='mismatch',
            total_rows_source=150,
            total_rows_target=140,
            matching_rows=120,
            missing_in_target=20,
            missing_in_source=10,
            mismatched_rows=10,
            comparison_time_sec=3.456,
            temp_table_name='tmp_mismatch_123'
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['match_status'] == 'mismatch'
        assert result_dict['total_rows_source'] == 150
        assert result_dict['total_rows_target'] == 140
        assert result_dict['matching_rows'] == 120
        assert result_dict['missing_in_target'] == 20
        assert result_dict['missing_in_source'] == 10
        assert result_dict['mismatched_rows'] == 10
        assert result_dict['comparison_time_sec'] == 3.46  # Rounded
        assert result_dict['temp_table_name'] == 'tmp_mismatch_123'
        assert result_dict['error_message'] is None

"""
Unit Tests for Session Manager
================================
Tests session lifecycle management and database operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.unit
@pytest.mark.services
class TestSessionManager:
    """Test SessionManager service class"""
    
    @pytest.mark.asyncio
    async def test_create_session(self, sample_session_data):
        """Test session creation"""
        from services.session_manager import SessionManager
        
        # Mock database pool
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        
        manager = SessionManager(mock_pool)
        
        result = await manager.create_session(**sample_session_data)
        
        assert result['session_id'] == 'test_session_001'
        assert result['status'] == 'pending'
        assert result['created'] is True
        assert mock_conn.execute.called
    
    @pytest.mark.asyncio
    async def test_update_session_status_running(self):
        """Test updating session to running status"""
        from services.session_manager import SessionManager
        
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        
        manager = SessionManager(mock_pool)
        
        await manager.update_session_status('test_001', 'running')
        
        # Should set started_at timestamp
        assert mock_conn.execute.called
        call_args = mock_conn.execute.call_args[0]
        assert 'started_at' in call_args[0]
    
    @pytest.mark.asyncio
    async def test_update_session_status_completed(self):
        """Test updating session to completed status"""
        from services.session_manager import SessionManager
        
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        
        manager = SessionManager(mock_pool)
        
        await manager.update_session_status('test_001', 'completed')
        
        # Should set completed_at and execution_time_ms
        assert mock_conn.execute.called
        call_args = mock_conn.execute.call_args[0]
        assert 'completed_at' in call_args[0]
        assert 'execution_time_ms' in call_args[0]
    
    @pytest.mark.asyncio
    async def test_add_file(self):
        """Test adding file to session"""
        from services.session_manager import SessionManager
        
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=123)
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        
        manager = SessionManager(mock_pool)
        
        file_id = await manager.add_file(
            session_id='test_001',
            file_role='source',
            file_path='tests/test_001/source.csv',
            file_name='source.csv',
            file_size=1024000,
            file_format='csv',
            row_count=5000,
            column_count=15
        )
        
        assert file_id == 123
        assert mock_conn.fetchval.called
    
    @pytest.mark.asyncio
    async def test_save_comparison_result(self, sample_comparison_result):
        """Test saving comparison result"""
        from services.session_manager import SessionManager
        
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=456)
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        
        manager = SessionManager(mock_pool)
        
        result_id = await manager.save_comparison_result(
            session_id='test_001',
            **sample_comparison_result
        )
        
        assert result_id == 456
        assert mock_conn.fetchval.called
    
    @pytest.mark.asyncio
    async def test_save_mismatch_details_batching(self, sample_mismatches):
        """Test that mismatches are inserted in batches"""
        from services.session_manager import SessionManager
        
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        
        manager = SessionManager(mock_pool)
        
        # Create large mismatch dataset
        large_mismatches = sample_mismatches * 500  # 1500 mismatches
        
        await manager.save_mismatch_details(
            result_id=456,
            mismatches=large_mismatches,
            batch_size=1000
        )
        
        # Should call executemany twice (1000 + 500)
        assert mock_conn.executemany.call_count == 2
    
    @pytest.mark.asyncio
    async def test_log_audit(self):
        """Test audit logging"""
        from services.session_manager import SessionManager
        
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        
        manager = SessionManager(mock_pool)
        
        await manager.log_audit(
            session_id='test_001',
            client_id='test-user',
            client_role='user',
            tool_name='compare_csv_files',
            action='compare',
            success=True,
            execution_time_ms=250,
            metadata={'rows_compared': 1000}
        )
        
        assert mock_conn.execute.called
        call_args = mock_conn.execute.call_args[0]
        assert 'audit_log' in call_args[0]
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self):
        """Test retrieving active sessions"""
        from services.session_manager import SessionManager
        
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {'session_id': 'test_001', 'status': 'running'},
            {'session_id': 'test_002', 'status': 'pending'}
        ])
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        
        manager = SessionManager(mock_pool)
        
        sessions = await manager.get_active_sessions()
        
        assert len(sessions) == 2
        assert sessions[0]['session_id'] == 'test_001'
        assert mock_conn.fetch.called
    
    @pytest.mark.asyncio
    async def test_get_active_sessions_filtered(self):
        """Test retrieving active sessions filtered by client"""
        from services.session_manager import SessionManager
        
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {'session_id': 'test_001', 'client_id': 'user1', 'status': 'running'}
        ])
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        
        manager = SessionManager(mock_pool)
        
        sessions = await manager.get_active_sessions(client_id='user1')
        
        assert len(sessions) == 1
        # Should use query with WHERE clause
        call_args = mock_conn.fetch.call_args[0]
        assert 'WHERE client_id' in call_args[0]


@pytest.mark.unit
@pytest.mark.database
class TestDatabasePool:
    """Test DatabasePool connection manager"""
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self, test_config):
        """Test database pool initialization"""
        from db.db_pool import DatabasePool
        
        with patch('db.db_pool.asyncpg.create_pool') as mock_create:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value='PostgreSQL 16.0')
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock()
            mock_create.return_value = mock_pool
            
            db_pool = DatabasePool(test_config)
            success = await db_pool.initialize()
            
            assert success is True
            assert mock_create.called
            assert db_pool.pool is not None
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, test_config):
        """Test successful health check"""
        from db.db_pool import DatabasePool
        
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.execute = AsyncMock()
        
        db_pool = DatabasePool(test_config)
        db_pool.pool = mock_pool
        db_pool.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        db_pool.pool.acquire.return_value.__aexit__ = AsyncMock()
        
        healthy = await db_pool.health_check()
        
        assert healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, test_config):
        """Test failed health check"""
        from db.db_pool import DatabasePool
        
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=Exception("Connection failed"))
        mock_conn.execute = AsyncMock()
        
        db_pool = DatabasePool(test_config)
        db_pool.pool = mock_pool
        db_pool.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        db_pool.pool.acquire.return_value.__aexit__ = AsyncMock()
        
        healthy = await db_pool.health_check()
        
        assert healthy is False

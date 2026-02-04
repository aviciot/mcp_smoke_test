"""
Pytest Configuration and Fixtures
===================================
Shared fixtures and configuration for all tests
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add server directory to path
server_dir = Path(__file__).parent.parent / "server"
sys.path.insert(0, str(server_dir))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Mock configuration for testing"""
    class MockConfig:
        def __init__(self):
            self._data = {
                'server': {
                    'authentication': {
                        'enabled': True,
                        'api_keys': []
                    }
                },
                'database': {
                    'host': 'localhost',
                    'port': 5436,
                    'name': 'mcp',
                    'schema': 'mcp_smoke',
                    'user': 'mcp',
                    'password': 'mcp',
                    'pool_size': 5
                }
            }
            self.auth_enabled = True
            self.api_keys = {}
        
        def get(self, key, default=None):
            keys = key.split('.')
            value = self._data
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            return value
    
    return MockConfig()


@pytest.fixture
def sample_api_keys():
    """Sample API keys for testing"""
    return {
        'admin-test-key-123': {
            'name': 'test-admin',
            'role': 'admin',
            'description': 'Test admin key'
        },
        'dba-test-key-123': {
            'name': 'test-dba',
            'role': 'dba',
            'description': 'Test DBA key'
        },
        'user-test-key-123': {
            'name': 'test-user',
            'role': 'user',
            'description': 'Test user key'
        }
    }


@pytest.fixture
def mock_request():
    """Mock Starlette request object"""
    class MockClient:
        host = "127.0.0.1"
    
    class MockState:
        pass
    
    class MockHeaders:
        def __init__(self):
            self._headers = {}
        
        def get(self, key, default=None):
            return self._headers.get(key.lower(), default)
        
        def set(self, key, value):
            self._headers[key.lower()] = value
    
    class MockURL:
        path = "/test"
    
    class MockRequest:
        def __init__(self):
            self.client = MockClient()
            self.state = MockState()
            self.headers = MockHeaders()
            self.url = MockURL()
    
    return MockRequest()


@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return {
        'session_id': 'test_session_001',
        'test_type': 'statement',
        'client_id': 'test-user',
        'client_role': 'user',
        'source_type': 'storagegrid',
        'target_type': 'storagegrid',
        'ignore_columns': ['timestamp', 'audit_user'],
        'report_format': 'html'
    }


@pytest.fixture
def sample_comparison_result():
    """Sample comparison result for testing"""
    return {
        'total_rows': 1000,
        'matched_rows': 950,
        'mismatched_rows': 50,
        'source_only_rows': 5,
        'target_only_rows': 3,
        'columns_compared': 15,
        'columns_with_differences': 3,
        'comparison_time_ms': 250
    }


@pytest.fixture
def sample_mismatches():
    """Sample mismatch data for testing"""
    return [
        {
            'row_number': 10,
            'row_key': 'TXN-001',
            'column_name': 'amount',
            'source_value': '100.00',
            'target_value': '100.50',
            'difference_type': 'value_mismatch'
        },
        {
            'row_number': 25,
            'row_key': 'TXN-002',
            'column_name': 'status',
            'source_value': 'active',
            'target_value': 'pending',
            'difference_type': 'value_mismatch'
        },
        {
            'row_number': 50,
            'column_name': 'description',
            'source_value': 'Payment received',
            'target_value': None,
            'difference_type': 'missing_target'
        }
    ]

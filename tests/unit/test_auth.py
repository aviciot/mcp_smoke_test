"""
Unit Tests for Authentication Middleware
=========================================
Tests API key authentication and session extraction
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib


@pytest.mark.unit
@pytest.mark.auth
class TestAuthMiddleware:
    """Test authentication middleware"""
    
    def test_extract_session_id_from_header(self, test_config, mock_request):
        """Test session ID extraction from X-Session-Id header"""
        from auth_middleware import AuthMiddleware
        
        middleware = AuthMiddleware(None, test_config)
        mock_request.headers.set('x-session-id', 'test-session-123')
        
        session_id = middleware._extract_session_id(mock_request)
        
        assert session_id == 'test-session-123'
    
    def test_extract_session_id_from_connection(self, test_config, mock_request):
        """Test session ID extraction from X-Connection-Id header"""
        from auth_middleware import AuthMiddleware
        
        middleware = AuthMiddleware(None, test_config)
        mock_request.headers.set('x-connection-id', 'conn-456')
        
        session_id = middleware._extract_session_id(mock_request)
        
        assert session_id == 'conn-456'
    
    def test_extract_session_id_fingerprint(self, test_config, mock_request):
        """Test session ID generation from client fingerprint"""
        from auth_middleware import AuthMiddleware
        
        middleware = AuthMiddleware(None, test_config)
        mock_request.headers.set('user-agent', 'TestAgent/1.0')
        
        session_id = middleware._extract_session_id(mock_request)
        
        # Should generate fingerprint-based session ID
        assert session_id.startswith('fp_')
        assert len(session_id) == 35  # fp_ + 32 char hash
    
    @pytest.mark.asyncio
    async def test_public_endpoint_bypass(self, test_config, mock_request):
        """Test that public endpoints bypass authentication"""
        from auth_middleware import AuthMiddleware
        
        call_next = AsyncMock(return_value="response")
        middleware = AuthMiddleware(None, test_config)
        
        # Test health endpoint
        mock_request.url.path = "/health"
        response = await middleware.dispatch(mock_request, call_next)
        
        assert call_next.called
        assert response == "response"
    
    @pytest.mark.asyncio
    async def test_missing_auth_header(self, test_config, mock_request):
        """Test rejection when Authorization header is missing"""
        from auth_middleware import AuthMiddleware
        
        call_next = AsyncMock()
        test_config.auth_enabled = True
        middleware = AuthMiddleware(None, test_config)
        
        mock_request.url.path = "/compare_csv_files"
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 401
        assert not call_next.called
    
    @pytest.mark.asyncio
    async def test_invalid_bearer_format(self, test_config, mock_request):
        """Test rejection of invalid Authorization format"""
        from auth_middleware import AuthMiddleware
        
        call_next = AsyncMock()
        test_config.auth_enabled = True
        middleware = AuthMiddleware(None, test_config)
        
        mock_request.url.path = "/compare_csv_files"
        mock_request.headers.set('authorization', 'InvalidFormat api-key-123')
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, test_config, mock_request):
        """Test rejection of invalid API key"""
        from auth_middleware import AuthMiddleware
        
        call_next = AsyncMock()
        test_config.auth_enabled = True
        test_config.api_keys = {'valid-key': {'name': 'test', 'role': 'user'}}
        middleware = AuthMiddleware(None, test_config)
        
        mock_request.url.path = "/compare_csv_files"
        mock_request.headers.set('authorization', 'Bearer invalid-key')
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_valid_authentication(self, test_config, mock_request, sample_api_keys):
        """Test successful authentication with valid API key"""
        from auth_middleware import AuthMiddleware
        
        call_next = AsyncMock(return_value="response")
        test_config.auth_enabled = True
        test_config.api_keys = sample_api_keys
        middleware = AuthMiddleware(None, test_config)
        
        mock_request.url.path = "/compare_csv_files"
        mock_request.headers.set('authorization', 'Bearer user-test-key-123')
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Should succeed and set request.state
        assert call_next.called
        assert response == "response"
        assert hasattr(mock_request.state, 'client_name')
        assert mock_request.state.client_name == 'test-user'
        assert mock_request.state.client_role == 'user'
    
    @pytest.mark.asyncio
    async def test_auth_disabled(self, test_config, mock_request):
        """Test that requests pass through when auth is disabled"""
        from auth_middleware import AuthMiddleware
        
        call_next = AsyncMock(return_value="response")
        test_config.auth_enabled = False
        middleware = AuthMiddleware(None, test_config)
        
        mock_request.url.path = "/compare_csv_files"
        # No Authorization header
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert call_next.called
        assert response == "response"


@pytest.mark.unit
@pytest.mark.auth
class TestToolAuth:
    """Test role-based access control decorator"""
    
    def test_get_user_info(self):
        """Test user info extraction from context"""
        from tools.tool_auth import get_user_info
        from tools.feedback_context import set_request_context
        
        # Set context
        set_request_context(
            session_id='test-session',
            user_id='test-user',
            client_id='test-user',
            client_role='admin'
        )
        
        user_info = get_user_info()
        
        assert user_info['client_id'] == 'test-user'
        assert user_info['role'] == 'admin'
        assert user_info['session_id'] == 'test-session'
    
    def test_require_roles_admin_access(self):
        """Test that admin role has access to all tools"""
        from tools.tool_auth import require_roles
        from tools.feedback_context import set_request_context
        
        # Set admin context
        set_request_context(
            session_id='test-session',
            user_id='admin-user',
            client_id='admin-user',
            client_role='admin'
        )
        
        @require_roles(['dba'])
        def restricted_tool():
            return "success"
        
        result = restricted_tool()
        
        # Admin should have access even though role requirement is 'dba'
        assert result == "success"
    
    def test_require_roles_allowed(self):
        """Test that users with correct role have access"""
        from tools.tool_auth import require_roles
        from tools.feedback_context import set_request_context
        
        # Set DBA context
        set_request_context(
            session_id='test-session',
            user_id='dba-user',
            client_id='dba-user',
            client_role='dba'
        )
        
        @require_roles(['dba', 'admin'])
        def restricted_tool():
            return "success"
        
        result = restricted_tool()
        
        assert result == "success"
    
    def test_require_roles_denied(self):
        """Test that users without correct role are denied"""
        from tools.tool_auth import require_roles
        from tools.feedback_context import set_request_context
        
        # Set user context
        set_request_context(
            session_id='test-session',
            user_id='regular-user',
            client_id='regular-user',
            client_role='user'
        )
        
        @require_roles(['dba', 'admin'])
        def restricted_tool():
            return "success"
        
        result = restricted_tool()
        
        # Should return error dict
        assert isinstance(result, dict)
        assert result['error'] == 'insufficient_permissions'
        assert result['your_role'] == 'user'
        assert 'dba' in result['required_roles']
    
    def test_check_role_access(self):
        """Test manual role checking"""
        from tools.tool_auth import check_role_access
        from tools.feedback_context import set_request_context
        
        # Set admin context
        set_request_context(
            session_id='test-session',
            user_id='admin-user',
            client_id='admin-user',
            client_role='admin'
        )
        
        has_access, message = check_role_access(['admin', 'dba'])
        
        assert has_access is True
        assert 'Admin' in message

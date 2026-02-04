# MCP Smoke Test - Testing Guide
================================

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── unit/                    # Fast unit tests (no external dependencies)
│   ├── test_auth.py        # Authentication middleware tests
│   ├── test_session_manager.py  # Session manager tests
│   └── test_services.py    # Service class tests
├── integration/             # Integration tests (require database)
│   ├── test_database.py    # Database integration tests
│   └── test_end_to_end.py  # Full workflow tests
└── README.md               # This file
```

## Running Tests

### All Tests
```bash
cd mcp_smoke
pytest
```

### Unit Tests Only (Fast)
```bash
pytest -m unit
```

### Integration Tests (Require Database)
```bash
pytest -m integration
```

### Specific Test File
```bash
pytest tests/unit/test_auth.py
```

### Specific Test Function
```bash
pytest tests/unit/test_auth.py::TestAuthMiddleware::test_valid_authentication
```

### With Coverage Report
```bash
pytest --cov=server --cov-report=html
# Open htmlcov/index.html in browser
```

### Verbose Output
```bash
pytest -v
```

## Test Markers

Tests are marked with categories:

- `@pytest.mark.unit` - Fast unit tests, no external dependencies
- `@pytest.mark.integration` - Require database or external services
- `@pytest.mark.slow` - Tests that take several seconds
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.database` - Database tests
- `@pytest.mark.services` - Service class tests
- `@pytest.mark.tools` - Tool tests

### Run by Marker
```bash
pytest -m auth         # Only authentication tests
pytest -m "not slow"   # Skip slow tests
pytest -m "unit and auth"  # Unit tests for auth
```

## Test Coverage

Current coverage goals:
- **Minimum:** 70%
- **Target:** 85%
- **Critical paths:** 95%+

### Coverage by Module
```bash
pytest --cov=server/auth_middleware --cov-report=term-missing
pytest --cov=server/services --cov-report=term-missing
pytest --cov=server/tools --cov-report=term-missing
```

## Writing Tests

### Unit Test Example
```python
import pytest

@pytest.mark.unit
@pytest.mark.auth
def test_example():
    """Test description"""
    # Arrange
    expected = "result"
    
    # Act
    actual = function_under_test()
    
    # Assert
    assert actual == expected
```

### Async Test Example
```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function"""
    result = await async_function()
    assert result is not None
```

### Using Fixtures
```python
def test_with_fixtures(test_config, sample_api_keys):
    """Test using fixtures from conftest.py"""
    assert test_config.auth_enabled is True
    assert len(sample_api_keys) == 3
```

## Integration Tests Setup

Integration tests require:
1. PostgreSQL running on localhost:5436
2. Database `mcp` with schema `mcp_smoke`
3. User `mcp` with password `mcp`

### Start Test Database
```bash
# Using docker-compose (if available)
docker-compose up -d postgres

# Or use existing pg_mcp database
psql -U mcp -d mcp -f ../pg_mcp/postgres-init/015_mcp_smoke_schema.sql
```

## Continuous Integration

Tests should run in CI pipeline:
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest -m unit                    # Always run unit tests
    pytest -m integration --maxfail=1 # Stop on first integration failure
```

## Test Data

### Fixtures Available (from conftest.py)
- `test_config` - Mock configuration
- `sample_api_keys` - Sample API keys for testing
- `mock_request` - Mock Starlette request object
- `sample_session_data` - Sample session data
- `sample_comparison_result` - Sample comparison metrics
- `sample_mismatches` - Sample mismatch records

### Creating Test Data
```python
@pytest.fixture
def custom_fixture():
    """Custom test data"""
    return {"key": "value"}
```

## Debugging Tests

### Run with Print Statements
```bash
pytest -s  # Don't capture stdout
```

### Debug Specific Test
```bash
pytest --pdb  # Drop into debugger on failure
```

### Show Locals on Failure
```bash
pytest -l  # Show local variables
```

## Best Practices

1. **Fast Unit Tests** - Mock external dependencies
2. **Descriptive Names** - Test name should describe what it tests
3. **One Assertion per Test** - Keep tests focused
4. **Arrange-Act-Assert** - Clear test structure
5. **Use Fixtures** - Reuse test data
6. **Test Error Cases** - Don't just test happy path
7. **Clean Up** - Tests should not leave side effects

## Current Test Status

### Phase 1: Authentication ✅
- ✅ Auth middleware tests (8 tests)
- ✅ Role-based access control tests (5 tests)

### Phase 2: Database & Session Management ✅
- ✅ Session manager tests (9 tests)
- ✅ Database pool tests (3 tests)

### Phase 3: Service Classes 🚧
- ⏳ StorageGrid client tests
- ⏳ CSV comparer tests
- ⏳ Report generator tests
- ⏳ Database exporter tests
- ⏳ File handler tests

### Phase 4: Tools 🚧
- ⏳ Smoke test orchestration tests
- ⏳ Comparison tools tests
- ⏳ File upload tests

## Running Example

```bash
$ pytest -v

tests/unit/test_auth.py::TestAuthMiddleware::test_extract_session_id_from_header PASSED
tests/unit/test_auth.py::TestAuthMiddleware::test_public_endpoint_bypass PASSED
tests/unit/test_auth.py::TestAuthMiddleware::test_valid_authentication PASSED
tests/unit/test_session_manager.py::TestSessionManager::test_create_session PASSED
tests/unit/test_session_manager.py::TestSessionManager::test_add_file PASSED

========================= 25 passed in 2.34s ==========================
```

## Next Steps

1. Add integration tests for database operations
2. Add service class tests as they're implemented
3. Add tool tests for MCP tool functions
4. Set up CI/CD pipeline
5. Aim for 85% code coverage

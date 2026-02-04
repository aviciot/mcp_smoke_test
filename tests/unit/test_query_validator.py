"""
Unit Tests for Query Validator
===============================
Comprehensive testing of read-only query enforcement
"""

import pytest
from server.services.query_validator import QueryValidator, ValidationResult, validate_query, is_query_safe


class TestQueryValidator:
    """Test QueryValidator class"""
    
    def test_simple_select_passes(self):
        """Test simple SELECT query passes validation"""
        validator = QueryValidator()
        result = validator.validate("SELECT * FROM users")
        
        assert result.is_safe is True
        assert len(result.violations) == 0
        assert result.query_type == "SELECT"
        assert result.sanitized_query == "SELECT * FROM users"
    
    def test_select_with_where_passes(self):
        """Test SELECT with WHERE clause passes"""
        validator = QueryValidator()
        result = validator.validate("""
            SELECT id, name, email 
            FROM users 
            WHERE status = 'active' 
            AND created_at > '2024-01-01'
        """)
        
        assert result.is_safe is True
        assert result.query_type == "SELECT"
    
    def test_select_with_join_passes(self):
        """Test SELECT with JOIN passes"""
        validator = QueryValidator()
        result = validator.validate("""
            SELECT u.id, u.name, o.order_date
            FROM users u
            INNER JOIN orders o ON u.id = o.user_id
            WHERE o.status = 'completed'
        """)
        
        assert result.is_safe is True
    
    def test_cte_with_passes(self):
        """Test WITH (CTE) query passes"""
        validator = QueryValidator()
        result = validator.validate("""
            WITH active_users AS (
                SELECT * FROM users WHERE status = 'active'
            )
            SELECT * FROM active_users
        """)
        
        assert result.is_safe is True
        assert result.query_type == "WITH"
    
    def test_insert_blocked(self):
        """Test INSERT query is blocked"""
        validator = QueryValidator()
        result = validator.validate("INSERT INTO users (name) VALUES ('John')")
        
        assert result.is_safe is False
        assert any('INSERT' in v for v in result.violations)
        assert result.sanitized_query is None
    
    def test_update_blocked(self):
        """Test UPDATE query is blocked"""
        validator = QueryValidator()
        result = validator.validate("UPDATE users SET name = 'John' WHERE id = 1")
        
        assert result.is_safe is False
        assert any('UPDATE' in v for v in result.violations)
    
    def test_delete_blocked(self):
        """Test DELETE query is blocked"""
        validator = QueryValidator()
        result = validator.validate("DELETE FROM users WHERE id = 1")
        
        assert result.is_safe is False
        assert any('DELETE' in v for v in result.violations)
    
    def test_drop_blocked(self):
        """Test DROP query is blocked"""
        validator = QueryValidator()
        result = validator.validate("DROP TABLE users")
        
        assert result.is_safe is False
        assert any('DROP' in v for v in result.violations)
    
    def test_truncate_blocked(self):
        """Test TRUNCATE query is blocked"""
        validator = QueryValidator()
        result = validator.validate("TRUNCATE TABLE users")
        
        assert result.is_safe is False
        assert any('TRUNCATE' in v for v in result.violations)
    
    def test_alter_blocked(self):
        """Test ALTER query is blocked"""
        validator = QueryValidator()
        result = validator.validate("ALTER TABLE users ADD COLUMN age INT")
        
        assert result.is_safe is False
        assert any('ALTER' in v for v in result.violations)
    
    def test_create_blocked(self):
        """Test CREATE query is blocked"""
        validator = QueryValidator()
        result = validator.validate("CREATE TABLE test (id INT)")
        
        assert result.is_safe is False
        assert any('CREATE' in v for v in result.violations)
    
    def test_execute_blocked(self):
        """Test EXECUTE is blocked (stored procedures)"""
        validator = QueryValidator()
        result = validator.validate("EXECUTE sp_dangerous_proc")
        
        assert result.is_safe is False
        assert any('EXECUTE' in v for v in result.violations)
    
    def test_call_blocked(self):
        """Test CALL is blocked (stored procedures)"""
        validator = QueryValidator()
        result = validator.validate("CALL sp_dangerous_proc()")
        
        assert result.is_safe is False
        assert any('CALL' in v for v in result.violations)
    
    def test_grant_blocked(self):
        """Test GRANT is blocked (permission changes)"""
        validator = QueryValidator()
        result = validator.validate("GRANT ALL ON users TO attacker")
        
        assert result.is_safe is False
        assert any('GRANT' in v for v in result.violations)
    
    def test_revoke_blocked(self):
        """Test REVOKE is blocked (permission changes)"""
        validator = QueryValidator()
        result = validator.validate("REVOKE ALL ON users FROM admin")
        
        assert result.is_safe is False
        assert any('REVOKE' in v for v in result.violations)
    
    def test_select_into_blocked(self):
        """Test SELECT INTO is blocked (creates tables)"""
        validator = QueryValidator()
        result = validator.validate("SELECT * INTO new_table FROM users")
        
        assert result.is_safe is False
        assert any('INTO' in v for v in result.violations)
    
    def test_multiple_statements_blocked(self):
        """Test multi-statement queries are blocked"""
        validator = QueryValidator()
        result = validator.validate("""
            SELECT * FROM users;
            DROP TABLE users;
        """)
        
        assert result.is_safe is False
        assert any('multi-statement' in v.lower() for v in result.violations)
    
    def test_sql_injection_union_blocked(self):
        """Test UNION injection attempts are blocked"""
        validator = QueryValidator()
        result = validator.validate("""
            SELECT * FROM users 
            UNION 
            SELECT * FROM passwords; DROP TABLE users;
        """)
        
        assert result.is_safe is False
        # Should fail on multiple statements or dangerous keywords
        assert len(result.violations) > 0
    
    def test_comment_with_dangerous_keyword_blocked(self):
        """Test comments hiding dangerous code are blocked"""
        validator = QueryValidator()
        result = validator.validate("""
            SELECT * FROM users /* DROP TABLE users */
        """)
        
        assert result.is_safe is False
        assert any('comment' in v.lower() for v in result.violations)
    
    def test_empty_query_blocked(self):
        """Test empty query is blocked"""
        validator = QueryValidator()
        result = validator.validate("")
        
        assert result.is_safe is False
        assert any('empty' in v.lower() for v in result.violations)
    
    def test_whitespace_only_blocked(self):
        """Test whitespace-only query is blocked"""
        validator = QueryValidator()
        result = validator.validate("   \n\t  ")
        
        assert result.is_safe is False
        assert any('empty' in v.lower() for v in result.violations)
    
    def test_trailing_semicolon_removed(self):
        """Test trailing semicolon is removed from sanitized query"""
        validator = QueryValidator()
        result = validator.validate("SELECT * FROM users;")
        
        assert result.is_safe is True
        assert result.sanitized_query == "SELECT * FROM users"
        assert not result.sanitized_query.endswith(';')
    
    def test_case_insensitive_keyword_detection(self):
        """Test keyword detection works regardless of case"""
        validator = QueryValidator()
        
        # Test various cases
        test_cases = [
            "InSeRt InTo users (name) VALUES ('test')",
            "UPDATE users SET name = 'test'",
            "DeLeTe FrOm users"
        ]
        
        for query in test_cases:
            result = validator.validate(query)
            assert result.is_safe is False
    
    def test_word_boundary_detection(self):
        """Test that word boundaries prevent false positives"""
        validator = QueryValidator()
        
        # These should PASS (not dangerous)
        result = validator.validate("SELECT inserted_date, updated_by FROM users")
        assert result.is_safe is True
        
        # This should FAIL (actual UPDATE keyword)
        result = validator.validate("SELECT * FROM users UPDATE")
        assert result.is_safe is False
    
    def test_stats_tracking(self):
        """Test validation statistics tracking"""
        validator = QueryValidator()
        
        # Run some validations
        validator.validate("SELECT * FROM users")  # Pass
        validator.validate("INSERT INTO users VALUES (1)")  # Blocked
        validator.validate("SELECT * FROM orders")  # Pass
        validator.validate("DELETE FROM orders")  # Blocked
        
        stats = validator.get_stats()
        
        assert stats['total_validations'] == 4
        assert stats['blocked_queries'] == 2
        assert stats['success_rate'] == 50.0
    
    def test_complex_select_passes(self):
        """Test complex SELECT with subqueries passes"""
        validator = QueryValidator()
        result = validator.validate("""
            SELECT 
                u.id,
                u.name,
                (SELECT COUNT(*) FROM orders WHERE user_id = u.id) as order_count,
                (SELECT MAX(order_date) FROM orders WHERE user_id = u.id) as last_order
            FROM users u
            WHERE EXISTS (
                SELECT 1 FROM orders o 
                WHERE o.user_id = u.id 
                AND o.status = 'completed'
            )
            ORDER BY u.name
            LIMIT 100
        """)
        
        assert result.is_safe is True
    
    def test_union_without_danger_passes(self):
        """Test UNION without dangerous keywords passes"""
        validator = QueryValidator()
        result = validator.validate("""
            SELECT id, name FROM active_users
            UNION
            SELECT id, name FROM inactive_users
        """)
        
        assert result.is_safe is True


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_validate_query_function(self):
        """Test validate_query convenience function"""
        result = validate_query("SELECT * FROM users")
        
        assert isinstance(result, ValidationResult)
        assert result.is_safe is True
    
    def test_is_query_safe_function(self):
        """Test is_query_safe convenience function"""
        assert is_query_safe("SELECT * FROM users") is True
        assert is_query_safe("DROP TABLE users") is False


class TestEdgeCases:
    """Test edge cases and unusual patterns"""
    
    def test_string_with_semicolon_passes(self):
        """Test query with semicolon in string literal passes"""
        validator = QueryValidator()
        result = validator.validate("""
            SELECT * FROM users WHERE bio = 'I love SQL; it is great'
        """)
        
        assert result.is_safe is True
    
    def test_merge_statement_blocked(self):
        """Test MERGE statement is blocked"""
        validator = QueryValidator()
        result = validator.validate("""
            MERGE INTO users USING source ON users.id = source.id
        """)
        
        assert result.is_safe is False
        assert any('MERGE' in v for v in result.violations)
    
    def test_replace_statement_blocked(self):
        """Test REPLACE statement is blocked (MySQL)"""
        validator = QueryValidator()
        result = validator.validate("REPLACE INTO users (id, name) VALUES (1, 'John')")
        
        assert result.is_safe is False
        assert any('REPLACE' in v for v in result.violations)
    
    def test_lock_table_blocked(self):
        """Test LOCK TABLE is blocked"""
        validator = QueryValidator()
        result = validator.validate("LOCK TABLE users WRITE")
        
        assert result.is_safe is False
        assert any('LOCK' in v for v in result.violations)

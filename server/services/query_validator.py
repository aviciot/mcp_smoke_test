"""
Query Validator - Ensures Only Read-Only Queries Execute
=========================================================
Multi-layer safety mechanism to block dangerous database operations
"""

import re
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of query validation"""
    is_safe: bool
    violations: List[str]
    sanitized_query: Optional[str]
    query_type: str  # SELECT, WITH, INVALID


class QueryValidator:
    """
    Validates database queries to ensure they are read-only
    
    Safety Checks:
    1. Must start with SELECT or WITH (for CTEs)
    2. No dangerous keywords (INSERT, UPDATE, DELETE, DROP, etc.)
    3. No EXECUTE/CALL (prevents stored procedure execution)
    4. No INTO (prevents SELECT INTO table creation)
    5. No semicolon chains (prevents multi-statement injection)
    6. No comments that might hide dangerous code
    """
    
    # Dangerous keywords that should NEVER appear in queries
    DANGEROUS_KEYWORDS = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER',
        'CREATE', 'GRANT', 'REVOKE', 'EXECUTE', 'CALL', 'EXEC',
        'MERGE', 'REPLACE', 'RENAME', 'LOCK', 'UNLOCK'
    ]
    
    # Allowed query types
    ALLOWED_STARTS = ['SELECT', 'WITH']
    
    def __init__(self):
        """Initialize query validator"""
        self.validation_count = 0
        self.blocked_count = 0
    
    def validate(self, query: str) -> ValidationResult:
        """
        Validate query is read-only and safe to execute
        
        Args:
            query: SQL query to validate
        
        Returns:
            ValidationResult with safety status and violations
        """
        self.validation_count += 1
        
        if not query or not query.strip():
            return ValidationResult(
                is_safe=False,
                violations=["Query is empty"],
                sanitized_query=None,
                query_type="INVALID"
            )
        
        # Remove extra whitespace and normalize
        query = query.strip()
        query_upper = query.upper()
        
        violations = []
        
        # Check 1: Must start with SELECT or WITH
        query_type = self._detect_query_type(query_upper)
        if query_type not in self.ALLOWED_STARTS:
            violations.append(
                f"Query must start with SELECT or WITH (for CTEs). "
                f"Found: {query_type}"
            )
        
        # Check 2: No dangerous keywords
        dangerous_found = self._check_dangerous_keywords(query_upper)
        if dangerous_found:
            violations.extend([
                f"Dangerous keyword '{keyword}' detected" 
                for keyword in dangerous_found
            ])
        
        # Check 3: No SELECT INTO (creates tables)
        if self._has_select_into(query_upper):
            violations.append("SELECT INTO is not allowed (creates new tables)")
        
        # Check 4: No multi-statement queries (SQL injection risk)
        if self._has_multiple_statements(query):
            violations.append(
                "Multi-statement queries not allowed (security risk). "
                "Found multiple semicolons."
            )
        
        # Check 5: No suspicious comments that might hide code
        if self._has_suspicious_comments(query):
            violations.append(
                "Suspicious comments detected that might hide dangerous code"
            )
        
        # Check 6: No UNION with dangerous keywords (advanced injection)
        if self._has_union_injection(query_upper):
            violations.append(
                "UNION with dangerous keywords detected (possible injection)"
            )
        
        is_safe = len(violations) == 0
        
        if not is_safe:
            self.blocked_count += 1
            logger.warning(
                f"🚫 Query blocked! Violations: {', '.join(violations)}"
            )
        
        # Sanitize query if safe
        sanitized_query = None
        if is_safe:
            sanitized_query = query.strip().rstrip(';')
        
        return ValidationResult(
            is_safe=is_safe,
            violations=violations,
            sanitized_query=sanitized_query,
            query_type=query_type
        )
    
    def _detect_query_type(self, query_upper: str) -> str:
        """Detect query type from first keyword"""
        # Remove leading whitespace and comments
        query_clean = re.sub(r'^[\s\n]+', '', query_upper)
        query_clean = re.sub(r'^/\*.*?\*/', '', query_clean, flags=re.DOTALL)
        query_clean = re.sub(r'^--.*\n', '', query_clean)
        
        for allowed in self.ALLOWED_STARTS:
            if query_clean.startswith(allowed):
                return allowed
        
        # Extract first word
        match = re.match(r'^(\w+)', query_clean)
        if match:
            return match.group(1)
        
        return "INVALID"
    
    def _check_dangerous_keywords(self, query_upper: str) -> List[str]:
        """Check for dangerous keywords using word boundaries"""
        found = []
        
        for keyword in self.DANGEROUS_KEYWORDS:
            # Use word boundaries to avoid false positives
            # e.g., "INSERTED_DATE" should not match "INSERT"
            pattern = rf'\b{keyword}\b'
            if re.search(pattern, query_upper):
                found.append(keyword)
        
        return found
    
    def _has_select_into(self, query_upper: str) -> bool:
        """Check for SELECT INTO pattern"""
        # SELECT ... INTO pattern
        return bool(re.search(r'\bSELECT\b.*\bINTO\b', query_upper, re.DOTALL))
    
    def _has_multiple_statements(self, query: str) -> bool:
        """Check for multiple statements separated by semicolons"""
        # Remove string literals (they might contain semicolons)
        query_no_strings = re.sub(r"'[^']*'", '', query)
        query_no_strings = re.sub(r'"[^"]*"', '', query_no_strings)
        
        # Count semicolons
        semicolon_count = query_no_strings.count(';')
        
        # Allow one trailing semicolon, but not multiple
        return semicolon_count > 1
    
    def _has_suspicious_comments(self, query: str) -> bool:
        """Check for comments that might hide dangerous code"""
        # Block comment with dangerous keywords
        block_comments = re.findall(r'/\*.*?\*/', query, re.DOTALL)
        for comment in block_comments:
            comment_upper = comment.upper()
            for keyword in self.DANGEROUS_KEYWORDS:
                if keyword in comment_upper:
                    return True
        
        # Line comment with dangerous keywords
        line_comments = re.findall(r'--.*$', query, re.MULTILINE)
        for comment in line_comments:
            comment_upper = comment.upper()
            for keyword in self.DANGEROUS_KEYWORDS:
                if keyword in comment_upper:
                    return True
        
        return False
    
    def _has_union_injection(self, query_upper: str) -> bool:
        """
        Check for UNION injection attempts
        
        Example: SELECT * FROM users UNION SELECT * FROM passwords; DROP TABLE users;
        """
        if 'UNION' not in query_upper:
            return False
        
        # Check if UNION is followed by dangerous keywords
        parts = query_upper.split('UNION')
        for part in parts[1:]:  # Check parts after UNION
            for keyword in self.DANGEROUS_KEYWORDS:
                if re.search(rf'\b{keyword}\b', part):
                    return True
        
        return False
    
    def get_stats(self) -> dict:
        """Get validation statistics"""
        return {
            'total_validations': self.validation_count,
            'blocked_queries': self.blocked_count,
            'success_rate': (
                (self.validation_count - self.blocked_count) / self.validation_count * 100
                if self.validation_count > 0 else 0
            )
        }


# Convenience functions
def validate_query(query: str) -> ValidationResult:
    """Quick validation function"""
    validator = QueryValidator()
    return validator.validate(query)


def is_query_safe(query: str) -> bool:
    """Simple boolean check"""
    result = validate_query(query)
    return result.is_safe

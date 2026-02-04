# Interactive Database Comparison Design
## Updated Requirements for mcp_smoke

---

## Overview

Users can compare database tables/queries interactively with LLM guidance. The system performs comparison **inside the database** using temp tables for efficiency.

**Key Changes:**
1. ❌ Removed DBA-only export tools
2. ✅ Added user-accessible table comparison
3. ✅ Interactive LLM-guided flow
4. ✅ Safety guards (read-only, execution plan checks)
5. ✅ In-database comparison using temp tables

---

## User Flow

### Interactive Conversation Example

```
User: "I want to compare database tables"

LLM: "I'll help you compare tables. Which database would you like to use?"
     Options: Oracle (PROD), MySQL (STAGING)

User: "Oracle PROD"

LLM: "Checking database availability... ✅ Connected
     
     How would you like to specify the data to compare?
     1. Table names (simpler)
     2. Custom queries (more flexible)"

User: "Table names"

LLM: "Source Configuration:
     - Table name: "
     
User: "TRANSACTIONS"

LLM: "Target Configuration:
     - Table name: "
     
User: "TRANSACTIONS_NEW"

LLM: "Optional filters:
     - WHERE clause (e.g., 'transaction_date >= 2026-01-01'): "
     
User: "transaction_date >= '2026-01-01'"

LLM: "Checking execution plan...
     
     Estimated rows: 125,000
     Estimated time: 45 seconds
     Memory required: 2.1 GB
     
     ✅ Query is safe to execute
     
     Columns to ignore (comma-separated, or press Enter to compare all): "
     
User: "last_modified, audit_timestamp"

LLM: "Starting comparison...
     
     Progress: |████████████████████| 100% (125,000 rows)
     
     ✅ Comparison complete!
     
     Results:
     - Total rows: 125,000
     - Matched: 123,500 (98.8%)
     - Mismatched: 1,500 (1.2%)
     - Source only: 50
     - Target only: 25
     
     Top differences:
     1. Column 'amount': 850 mismatches
     2. Column 'status': 450 mismatches
     3. Column 'description': 200 mismatches
     
     Download detailed report: comparison_stmt_20260204_143015.zip"
```

---

## Safety Mechanisms

### 1. Database Availability Check
**Before any operation, verify database is accessible**

```python
class DatabaseValidator:
    async def check_availability(self, db_config: Dict) -> AvailabilityResult:
        """
        Check if database is available and responsive
        
        Returns:
            AvailabilityResult with status, latency, version
        """
        try:
            # Ping database with timeout
            start = time.time()
            version = await db.execute("SELECT VERSION()")
            latency_ms = (time.time() - start) * 1000
            
            return AvailabilityResult(
                available=True,
                latency_ms=latency_ms,
                version=version,
                message="Database is responsive"
            )
        except Exception as e:
            return AvailabilityResult(
                available=False,
                error=str(e),
                message="Database unavailable"
            )
```

**LLM Behavior:**
- ❌ If DB unavailable → Stop immediately, notify user, suggest troubleshooting
- ✅ If DB available → Proceed with comparison

---

### 2. Query Safety Validation
**Block dangerous queries - allow only SELECT statements**

```python
class QueryValidator:
    # Dangerous keywords that should never appear
    DANGEROUS_KEYWORDS = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER',
        'CREATE', 'GRANT', 'REVOKE', 'EXECUTE', 'CALL'
    ]
    
    # Required keywords for read-only queries
    REQUIRED_KEYWORDS = ['SELECT']
    
    def validate_query(self, query: str) -> ValidationResult:
        """
        Validate query is read-only and safe
        
        Checks:
        1. Must start with SELECT (or WITH for CTEs)
        2. No dangerous keywords (INSERT, UPDATE, DELETE, etc.)
        3. No EXECUTE/CALL (prevents stored procedure execution)
        4. No INTO (prevents SELECT INTO table creation)
        5. No semicolon chains (prevents multi-statement)
        
        Returns:
            ValidationResult with is_safe, violations, sanitized_query
        """
        query_upper = query.upper().strip()
        violations = []
        
        # Check dangerous keywords
        for keyword in self.DANGEROUS_KEYWORDS:
            if re.search(rf'\b{keyword}\b', query_upper):
                violations.append(f"Dangerous keyword '{keyword}' detected")
        
        # Must be SELECT or CTE (WITH)
        if not (query_upper.startswith('SELECT') or query_upper.startswith('WITH')):
            violations.append("Query must start with SELECT or WITH")
        
        # No SELECT INTO
        if 'INTO' in query_upper:
            violations.append("SELECT INTO is not allowed")
        
        # No multi-statement (check for semicolons)
        if query.count(';') > 1:
            violations.append("Multi-statement queries not allowed")
        
        is_safe = len(violations) == 0
        
        return ValidationResult(
            is_safe=is_safe,
            violations=violations,
            sanitized_query=query.strip().rstrip(';') if is_safe else None
        )
```

**Example Blocked Queries:**
```sql
-- ❌ BLOCKED
DELETE FROM transactions WHERE id = 1
UPDATE transactions SET status = 'cancelled'
DROP TABLE transactions
INSERT INTO transactions SELECT * FROM other_table
EXECUTE sp_dangerous_procedure
SELECT * FROM users; DELETE FROM logs;  -- Multi-statement

-- ✅ ALLOWED
SELECT * FROM transactions WHERE date >= '2026-01-01'
SELECT COUNT(*) FROM transactions
WITH cte AS (SELECT * FROM t1) SELECT * FROM cte
```

---

### 3. Execution Plan Analysis
**Check if query will take too long (>5 minutes)**

```python
class ExecutionPlanAnalyzer:
    MAX_EXECUTION_TIME_SEC = 300  # 5 minutes
    
    async def analyze_query_cost(self, db: Database, query: str) -> QueryCostResult:
        """
        Analyze query execution plan and estimate cost
        
        Returns:
            QueryCostResult with estimated_time, estimated_rows, warnings
        """
        # Get execution plan (Oracle/MySQL)
        if db.type == 'oracle':
            plan = await db.execute(f"EXPLAIN PLAN FOR {query}")
            plan_table = await db.fetch("SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY)")
            
        elif db.type == 'mysql':
            plan = await db.fetch(f"EXPLAIN {query}")
        
        # Parse plan for cost metrics
        estimated_rows = self._extract_row_count(plan)
        estimated_time_sec = self._estimate_time(plan, estimated_rows)
        
        warnings = []
        is_acceptable = True
        
        # Check if query is too expensive
        if estimated_time_sec > self.MAX_EXECUTION_TIME_SEC:
            warnings.append(
                f"Query estimated to take {estimated_time_sec}s (>{self.MAX_EXECUTION_TIME_SEC}s limit)"
            )
            is_acceptable = False
        
        # Check for full table scans on large tables
        if self._has_full_table_scan(plan) and estimated_rows > 1_000_000:
            warnings.append(
                f"Full table scan detected on {estimated_rows:,} rows - consider adding indexes"
            )
        
        return QueryCostResult(
            estimated_time_sec=estimated_time_sec,
            estimated_rows=estimated_rows,
            estimated_memory_mb=estimated_rows * 0.001,  # Rough estimate
            warnings=warnings,
            is_acceptable=is_acceptable,
            execution_plan=plan
        )
```

**LLM Behavior Based on Cost:**

```python
# Low cost (< 1 minute, < 100K rows)
"✅ Query looks efficient. Proceeding with comparison..."

# Medium cost (1-5 minutes, 100K-1M rows)
"⚠️  Query will take approximately 3 minutes to execute.
    Estimated rows: 500,000
    
    Would you like to:
    1. Proceed anyway
    2. Add filters to reduce data (recommended)
    3. Cancel"

# High cost (> 5 minutes or > 1M rows)
"❌ Query is too expensive to execute safely:
    
    Estimated time: 8 minutes (limit: 5 minutes)
    Estimated rows: 2,500,000
    
    Recommendations:
    1. Add WHERE clause to filter data (e.g., date range)
    2. Compare specific partitions instead of full table
    3. Contact DBA for large-scale comparison
    
    Example filtered query:
    SELECT * FROM transactions 
    WHERE transaction_date BETWEEN '2026-01-01' AND '2026-01-31'
    
    Would you like to modify the query?"
```

---

## In-Database Comparison Architecture

### Why Compare in Database?
1. ✅ **Performance** - No data transfer overhead
2. ✅ **Memory Efficient** - DB handles large datasets
3. ✅ **Leverages DB Power** - Uses indexes, parallel execution
4. ✅ **Temp Tables** - Automatic cleanup

### Comparison Strategy

```python
class DatabaseComparer:
    async def compare_tables(
        self,
        db: Database,
        source_query: str,
        target_query: str,
        join_columns: List[str],
        compare_columns: Optional[List[str]] = None,
        ignore_columns: Optional[List[str]] = None
    ) -> ComparisonResult:
        """
        Compare two queries/tables entirely in database using temp tables
        
        Process:
        1. Create temp table for source query results
        2. Create temp table for target query results
        3. Perform comparison using SQL FULL OUTER JOIN
        4. Store mismatches in temp table
        5. Fetch summary statistics
        6. Optionally fetch detailed mismatches
        7. Cleanup temp tables
        """
        
        session_id = self._generate_session_id()
        
        try:
            # Step 1: Create temp tables
            await self._create_temp_table(
                db, f"temp_source_{session_id}", source_query
            )
            
            await self._create_temp_table(
                db, f"temp_target_{session_id}", target_query
            )
            
            # Step 2: Determine columns to compare
            if compare_columns is None:
                # Get common columns from both tables
                compare_columns = await self._get_common_columns(
                    db, f"temp_source_{session_id}", f"temp_target_{session_id}"
                )
            
            # Remove ignored columns
            if ignore_columns:
                compare_columns = [c for c in compare_columns if c not in ignore_columns]
            
            # Step 3: Perform comparison in database
            comparison_sql = self._build_comparison_query(
                source_table=f"temp_source_{session_id}",
                target_table=f"temp_target_{session_id}",
                join_columns=join_columns,
                compare_columns=compare_columns
            )
            
            # Create temp table with mismatches
            await db.execute(f"""
                CREATE TEMPORARY TABLE temp_mismatches_{session_id} AS
                {comparison_sql}
            """)
            
            # Step 4: Get summary statistics
            summary = await self._get_comparison_summary(
                db, f"temp_mismatches_{session_id}"
            )
            
            # Step 5: Optionally fetch detailed mismatches
            if summary['mismatch_count'] > 0 and summary['mismatch_count'] <= 10000:
                mismatches = await db.fetch(f"""
                    SELECT * FROM temp_mismatches_{session_id}
                    LIMIT 10000
                """)
            else:
                mismatches = []
            
            return ComparisonResult(
                summary=summary,
                mismatches=mismatches,
                temp_table=f"temp_mismatches_{session_id}"  # For later export
            )
            
        finally:
            # Step 6: Cleanup temp tables
            await self._cleanup_temp_tables(db, session_id)
    
    def _build_comparison_query(
        self,
        source_table: str,
        target_table: str,
        join_columns: List[str],
        compare_columns: List[str]
    ) -> str:
        """
        Build SQL query that compares two tables and returns mismatches
        
        Strategy: FULL OUTER JOIN with COALESCE for null handling
        """
        
        # Build join condition
        join_conditions = [
            f"s.{col} = t.{col}" for col in join_columns
        ]
        join_clause = " AND ".join(join_conditions)
        
        # Build comparison conditions
        comparison_conditions = []
        for col in compare_columns:
            # Use COALESCE to handle NULLs
            comparison_conditions.append(
                f"COALESCE(CAST(s.{col} AS VARCHAR), 'NULL') != "
                f"COALESCE(CAST(t.{col} AS VARCHAR), 'NULL')"
            )
        
        comparison_clause = " OR ".join(comparison_conditions)
        
        # Build column list with source/target prefixes
        select_columns = []
        for col in join_columns + compare_columns:
            select_columns.append(f"s.{col} AS source_{col}")
            select_columns.append(f"t.{col} AS target_{col}")
        
        # Build CASE statements for difference detection
        difference_columns = []
        for col in compare_columns:
            difference_columns.append(f"""
                CASE 
                    WHEN s.{col} IS NULL THEN 'MISSING_SOURCE'
                    WHEN t.{col} IS NULL THEN 'MISSING_TARGET'
                    WHEN COALESCE(CAST(s.{col} AS VARCHAR), '') != 
                         COALESCE(CAST(t.{col} AS VARCHAR), '') 
                    THEN 'VALUE_MISMATCH'
                    ELSE 'MATCH'
                END AS {col}_diff_type
            """)
        
        # Final query
        query = f"""
        SELECT 
            {', '.join(select_columns)},
            {', '.join(difference_columns)},
            CASE 
                WHEN s.{join_columns[0]} IS NULL THEN 'TARGET_ONLY'
                WHEN t.{join_columns[0]} IS NULL THEN 'SOURCE_ONLY'
                ELSE 'BOTH'
            END AS row_status
        FROM {source_table} s
        FULL OUTER JOIN {target_table} t ON {join_clause}
        WHERE 
            s.{join_columns[0]} IS NULL OR 
            t.{join_columns[0]} IS NULL OR
            ({comparison_clause})
        """
        
        return query
```

### Example Comparison SQL

```sql
-- Compare TRANSACTIONS table between environments
-- Source: PROD.TRANSACTIONS
-- Target: UAT.TRANSACTIONS
-- Join on: transaction_id
-- Compare: amount, status, description

CREATE TEMPORARY TABLE temp_source_abc123 AS
SELECT * FROM PROD.TRANSACTIONS 
WHERE transaction_date >= '2026-01-01';

CREATE TEMPORARY TABLE temp_target_abc123 AS
SELECT * FROM UAT.TRANSACTIONS 
WHERE transaction_date >= '2026-01-01';

CREATE TEMPORARY TABLE temp_mismatches_abc123 AS
SELECT 
    s.transaction_id AS source_transaction_id,
    t.transaction_id AS target_transaction_id,
    s.amount AS source_amount,
    t.amount AS target_amount,
    s.status AS source_status,
    t.status AS target_status,
    CASE 
        WHEN s.amount IS NULL THEN 'MISSING_SOURCE'
        WHEN t.amount IS NULL THEN 'MISSING_TARGET'
        WHEN s.amount != t.amount THEN 'VALUE_MISMATCH'
        ELSE 'MATCH'
    END AS amount_diff_type,
    CASE 
        WHEN s.transaction_id IS NULL THEN 'TARGET_ONLY'
        WHEN t.transaction_id IS NULL THEN 'SOURCE_ONLY'
        ELSE 'BOTH'
    END AS row_status
FROM temp_source_abc123 s
FULL OUTER JOIN temp_target_abc123 t 
    ON s.transaction_id = t.transaction_id
WHERE 
    s.transaction_id IS NULL OR 
    t.transaction_id IS NULL OR
    (s.amount != t.amount OR s.status != t.status);

-- Get summary
SELECT 
    COUNT(*) AS total_mismatches,
    SUM(CASE WHEN row_status = 'SOURCE_ONLY' THEN 1 ELSE 0 END) AS source_only,
    SUM(CASE WHEN row_status = 'TARGET_ONLY' THEN 1 ELSE 0 END) AS target_only,
    SUM(CASE WHEN row_status = 'BOTH' THEN 1 ELSE 0 END) AS value_mismatches
FROM temp_mismatches_abc123;

-- Cleanup
DROP TABLE temp_source_abc123;
DROP TABLE temp_target_abc123;
DROP TABLE temp_mismatches_abc123;
```

---

## Tools Updated

### New Tool: compare_database_tables

```python
@mcp.tool(
    name="compare_database_tables",
    description="Compare database tables or query results interactively with safety checks"
)
def compare_database_tables(
    session_id: str,
    db_name: str,  # Predefined: oracle_prod, mysql_staging, etc.
    comparison_mode: str,  # "tables" or "queries"
    source_spec: str,  # Table name or query
    target_spec: str,  # Table name or query
    join_columns: List[str],  # Columns to join on (primary keys)
    where_clause: Optional[str] = None,  # Additional filter
    ignore_columns: Optional[List[str]] = None,
    skip_execution_plan_check: bool = False  # Admin override only
) -> Dict[str, Any]:
    """
    Interactive database comparison with safety guardrails
    
    Safety Checks:
    1. ✅ Database availability
    2. ✅ Query validation (read-only)
    3. ✅ Execution plan analysis (< 5 min)
    4. ✅ In-database comparison using temp tables
    
    Returns:
        Comparison summary with mismatch statistics
    """
```

**Removed Tools:**
- ❌ `export_database_table` (DBA-only, no longer needed)

---

## Updated Roles

### Simplified Role Model

| Role | Database Comparison | Other Tools |
|------|-------------------|-------------|
| **admin** | ✅ Full access (can skip execution plan checks) | ✅ All tools |
| **user** | ✅ Full access (must pass safety checks) | ✅ Smoke tests, CSV comparison, file upload |

**Removed Role:**
- ❌ DBA role (no longer needed without export tools)

---

## Configuration Updates

### Predefined Database Connections

```yaml
# settings.yaml
databases:
  oracle_prod:
    type: oracle
    host: "${ORACLE_PROD_HOST}"
    port: 1521
    service_name: "${ORACLE_PROD_SERVICE}"
    user: "${ORACLE_PROD_USER}"
    password: "${ORACLE_PROD_PASSWORD}"
    max_execution_time_sec: 300  # 5 minutes
    
  mysql_staging:
    type: mysql
    host: "${MYSQL_STAGING_HOST}"
    port: 3306
    database: "${MYSQL_STAGING_DB}"
    user: "${MYSQL_STAGING_USER}"
    password: "${MYSQL_STAGING_PASSWORD}"
    max_execution_time_sec: 300
```

---

## Success Criteria

✅ Users can compare tables without DBA permissions  
✅ Interactive LLM guidance through comparison flow  
✅ Database availability checked before operations  
✅ Only read-only queries allowed (multi-layer validation)  
✅ Execution plan analyzed, expensive queries blocked  
✅ Comparison performed in-database using temp tables  
✅ Detailed mismatch reports generated  
✅ Automatic cleanup of temp tables  
✅ Performance optimized for tables up to 1M rows  

---

## Implementation Priority

1. ✅ **Phase 1:** Remove DBA export tools
2. ✅ **Phase 2:** Implement QueryValidator (read-only checks)
3. ✅ **Phase 3:** Implement ExecutionPlanAnalyzer
4. ✅ **Phase 4:** Implement DatabaseComparer (in-DB comparison)
5. ✅ **Phase 5:** Create compare_database_tables tool
6. ✅ **Phase 6:** Update tests and documentation

---

**Next Steps:** Implement these changes in server code!

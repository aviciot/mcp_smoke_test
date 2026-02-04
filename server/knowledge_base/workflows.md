# Common Workflows

This guide provides step-by-step workflows for common MCP Smoke Test usage scenarios.

---

## Workflow 1: Simple Table Comparison

**Goal**: Compare two tables with identical structure in different databases.

### Step-by-Step

1. **List Available Databases**
   ```python
   list_available_databases()
   ```
   
   **Response:**
   ```json
   {
     "databases_by_type": {
       "oracle": ["oracle_statements", "oracle_billings", "oracle_transformer"],
       "mysql": ["mysql_brian", "mysql_prod"],
       "postgresql": ["postgres_prod", "postgres_test"]
     }
   }
   ```

2. **Choose Source and Target**
   - Source: `oracle_statements`
   - Target: `oracle_billings`

3. **Define Queries**
   ```python
   source_query = "SELECT * FROM orders"
   target_query = "SELECT * FROM orders"
   ```

4. **Identify Key Columns**
   - Key: `["order_id"]` (primary key for joining)

5. **Run Comparison**
   ```python
   compare_database_tables(
       source_database="oracle_statements",
       target_database="oracle_billings",
       source_query="SELECT * FROM orders",
       target_query="SELECT * FROM orders",
       key_columns=["order_id"]
   )
   ```

6. **Review Results**
   ```json
   {
     "comparison_summary": {
       "total_rows_source": 1500,
       "total_rows_target": 1498,
       "missing_in_target": 5,
       "extra_in_target": 3,
       "value_differences": 12
     },
     "missing_rows": [
       {"order_id": 1001, "source_values": {...}},
       {"order_id": 1005, "source_values": {...}}
     ],
     "different_values": [
       {
         "order_id": 2001,
         "column": "amount",
         "source_value": 150.00,
         "target_value": 145.00
       }
     ]
   }
   ```

---

## Workflow 2: Filtered Comparison

**Goal**: Compare only specific records matching certain criteria.

### Step-by-Step

1. **Define Filtered Queries**
   ```python
   # Only compare active orders from last 30 days
   source_query = """
       SELECT order_id, customer_id, amount, status
       FROM orders
       WHERE status = 'ACTIVE'
         AND order_date >= SYSDATE - 30
   """
   
   target_query = """
       SELECT order_id, customer_id, amount, status
       FROM orders
       WHERE status = 'ACTIVE'
         AND order_date >= CURDATE() - INTERVAL 30 DAY
   """
   ```

2. **Specify Columns to Compare**
   ```python
   compare_columns = ["customer_id", "amount", "status"]
   ```

3. **Run Comparison**
   ```python
   compare_database_tables(
       source_database="oracle_statements",
       target_database="mysql_brian",
       source_query=source_query,
       target_query=target_query,
       key_columns=["order_id"],
       compare_columns=compare_columns
   )
   ```

---

## Workflow 3: Cross-Database Type Comparison

**Goal**: Compare data between different database types (e.g., Oracle to MySQL).

### Considerations

- **Date Functions**: Different syntax
  - Oracle: `SYSDATE`, `TRUNC(date)`
  - MySQL: `CURDATE()`, `DATE(datetime)`
  - PostgreSQL: `CURRENT_DATE`, `DATE_TRUNC('day', timestamp)`

- **String Functions**: Different syntax
  - Oracle: `NVL(column, 'default')`
  - MySQL: `IFNULL(column, 'default')`
  - PostgreSQL: `COALESCE(column, 'default')`

### Example

```python
# Oracle source
source_query = """
    SELECT 
        customer_id,
        NVL(email, 'no-email@company.com') as email,
        TRUNC(created_date) as created_date
    FROM customers
    WHERE created_date >= SYSDATE - 90
"""

# MySQL target
target_query = """
    SELECT 
        customer_id,
        IFNULL(email, 'no-email@company.com') as email,
        DATE(created_date) as created_date
    FROM customers
    WHERE created_date >= CURDATE() - INTERVAL 90 DAY
"""

compare_database_tables(
    source_database="oracle_statements",
    target_database="mysql_brian",
    source_query=source_query,
    target_query=target_query,
    key_columns=["customer_id"]
)
```

---

## Workflow 4: Handling Safety Warnings

**Goal**: Understand and respond to safety mechanism warnings.

### Scenario: Query Validation Failure

**Error:**
```json
{
  "error": "Query validation failed",
  "reason": "Dangerous keyword detected: DELETE",
  "blocked_query": "DELETE FROM orders WHERE..."
}
```

**Solution:**
- Only SELECT statements are allowed
- Remove DELETE/UPDATE/INSERT operations
- Use WHERE clause to filter instead of DELETE

### Scenario: Database Unavailable

**Error:**
```json
{
  "error": "Database availability check failed",
  "database": "oracle_statements",
  "reason": "Connection timeout after 5000ms"
}
```

**Solution:**
- Check if database is online
- Verify network connectivity
- Confirm database credentials in settings.yaml
- Check firewall rules

### Scenario: Execution Time Exceeded

**Warning:**
```json
{
  "warning": "Estimated execution time exceeds 5 minutes",
  "estimated_time_sec": 420,
  "query_cost": 850000,
  "recommendation": "Add WHERE clause to reduce result set"
}
```

**Solution:**
- Add more specific WHERE clauses
- Reduce date range
- Filter by indexed columns
- Or: Admin can use `override_safety=true`

### Admin Override

```python
compare_database_tables(
    source_database="oracle_statements",
    target_database="oracle_billings",
    source_query="SELECT * FROM large_table",  # Very large query
    target_query="SELECT * FROM large_table",
    key_columns=["id"],
    override_safety=true  # Admin only!
)
```

---

## Workflow 5: Composite Key Comparison

**Goal**: Compare tables with multi-column primary keys.

### Example

```python
# Tables with composite key: (customer_id, order_date)
compare_database_tables(
    source_database="oracle_statements",
    target_database="oracle_billings",
    source_query="SELECT * FROM order_details",
    target_query="SELECT * FROM order_details",
    key_columns=["customer_id", "order_date"]  # Multiple keys
)
```

### Results with Composite Keys

```json
{
  "missing_rows": [
    {
      "customer_id": 1001,
      "order_date": "2026-02-01",
      "source_values": {"amount": 150.00}
    }
  ]
}
```

---

## Workflow 6: Learning About Safety Mechanisms

**Goal**: Understand what safety checks are in place.

### Get Safety Information

```python
get_comparison_safety_info()
```

**Response:**
```json
{
  "safety_layers": {
    "1_query_validation": {
      "purpose": "Enforce read-only queries",
      "checks": [
        "Only SELECT statements allowed",
        "Blocks: DROP, DELETE, UPDATE, INSERT, etc.",
        "Allows: WITH, subqueries, JOINs"
      ],
      "test_coverage": "33 tests, 93% coverage"
    },
    "2_database_availability": {
      "purpose": "Verify database connectivity",
      "checks": [
        "Connection test before operations",
        "5-second timeout",
        "Fail-fast approach"
      ],
      "test_coverage": "5 tests, 90% coverage"
    },
    "3_execution_plan_analysis": {
      "purpose": "Estimate query execution time",
      "checks": [
        "Analyzes EXPLAIN plan",
        "Blocks if estimated > 5 minutes",
        "Admin can override"
      ],
      "test_coverage": "16 tests, 94% coverage"
    },
    "4_database_comparer": {
      "purpose": "Safe in-database comparison",
      "checks": [
        "Uses temporary tables",
        "JOIN-based comparison",
        "Automatic cleanup"
      ],
      "test_coverage": "11 tests, 93% coverage"
    }
  }
}
```

---

## Workflow 7: Interactive LLM-Guided Comparison

**Goal**: Let the LLM guide you through the entire comparison process.

### Conversation Flow

**User:** "I need to compare data between two databases"

**LLM:** "I can help you with that! First, let me show you the available databases."
```python
list_available_databases()
```

**LLM:** "Here are the available databases:
- Oracle: statements, billings, transformer
- MySQL: brian, prod
- PostgreSQL: prod, test

Which source and target databases would you like to compare?"

**User:** "Compare oracle_statements with oracle_billings"

**LLM:** "Great! What table and filters would you like to query in oracle_statements?"

**User:** "Select all orders from the last month"

**LLM:** "I'll construct the query for you. For Oracle, I'll use:"
```sql
SELECT * FROM orders 
WHERE order_date >= SYSDATE - 30
```

**LLM:** "Should I use the same query for oracle_billings?"

**User:** "Yes"

**LLM:** "What column(s) should I use as the join key? Typically this is the primary key like 'order_id'."

**User:** "order_id"

**LLM:** "Perfect! Let me run the comparison with these 4 safety checks:
1. ✅ Query validation (read-only)
2. ✅ Database availability
3. ✅ Execution plan analysis
4. ✅ In-database comparison"

```python
compare_database_tables(
    source_database="oracle_statements",
    target_database="oracle_billings",
    source_query="SELECT * FROM orders WHERE order_date >= SYSDATE - 30",
    target_query="SELECT * FROM orders WHERE order_date >= SYSDATE - 30",
    key_columns=["order_id"]
)
```

**LLM:** "Comparison complete! Here are the results:
- Total rows in source: 1,245
- Total rows in target: 1,243
- Missing in target: 2 rows
- Value differences: 5 rows

Would you like to see the details of the missing or different rows?"

---

## Workflow 8: Migration Verification

**Goal**: Verify data after migration from PostgreSQL to Oracle.

### Step-by-Step

1. **Pre-Migration Snapshot**
   ```python
   # Get row count from PostgreSQL source
   compare_database_tables(
       source_database="postgres_prod",
       target_database="postgres_prod",  # Same database
       source_query="SELECT customer_id FROM customers",
       target_query="SELECT customer_id FROM customers",
       key_columns=["customer_id"]
   )
   # Expect: 0 differences (baseline check)
   ```

2. **Post-Migration Verification**
   ```python
   # Compare PostgreSQL source with Oracle target
   compare_database_tables(
       source_database="postgres_prod",
       target_database="oracle_statements",
       source_query="SELECT * FROM customers ORDER BY customer_id",
       target_query="SELECT * FROM customers ORDER BY customer_id",
       key_columns=["customer_id"]
   )
   ```

3. **Review Discrepancies**
   - Missing rows: Data not migrated
   - Extra rows: Duplicate migration
   - Value differences: Data type conversion issues

---

## Tips and Best Practices

### Query Optimization
- ✅ **DO**: Use indexed columns in WHERE clauses
- ✅ **DO**: Add date range filters
- ✅ **DO**: Specify exact columns needed
- ❌ **DON'T**: Use `SELECT *` on huge tables without filters

### Key Column Selection
- ✅ **DO**: Use primary key columns
- ✅ **DO**: Use unique identifiers
- ❌ **DON'T**: Use nullable columns as keys
- ❌ **DON'T**: Use columns with duplicates

### Error Handling
- ✅ **DO**: Check `list_available_databases()` first
- ✅ **DO**: Test queries on small datasets first
- ✅ **DO**: Read error messages carefully
- ❌ **DON'T**: Ignore safety warnings

### Performance
- ✅ **DO**: Compare similar-sized result sets
- ✅ **DO**: Use `compare_columns` to limit comparisons
- ✅ **DO**: Add WHERE clauses to reduce row count
- ❌ **DON'T**: Compare entire tables without filters

---

## Next Steps

- Read [overview.md](overview.md) for system capabilities
- Read [architecture.md](architecture.md) for internals
- Read [troubleshooting.md](troubleshooting.md) for issues

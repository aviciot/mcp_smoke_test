# MCP Smoke Test Overview

## What is MCP Smoke Test?

**MCP Smoke Test Server** is a specialized Model Context Protocol server designed for **safe, interactive database table comparison** across Oracle, MySQL, and PostgreSQL databases. It features a comprehensive 4-layer safety system that prevents dangerous queries and provides LLM-guided workflows.

### Unique Value Proposition

- **Interactive LLM-Guided Flow**: The MCP tools enable conversational workflows where the LLM guides users step-by-step
- **4-Layer Safety Architecture**: Query validation, database availability checks, execution plan analysis, and in-database comparison
- **Predefined Database Configuration**: Reference databases by name (e.g., 'oracle_statements') instead of connection strings
- **Read-Only Enforcement**: All queries are validated to ensure they are SELECT statements only

---

## What This MCP Does

✅ **Database Table Comparison**
- Compare data between two database tables
- Support for custom SELECT queries with WHERE clauses
- Identify missing rows, extra rows, and value differences
- Efficient in-database comparison using temporary tables

✅ **Safety Mechanisms**
- **QueryValidator**: Enforces read-only queries, blocks dangerous keywords (DROP, DELETE, UPDATE, etc.)
- **DatabaseValidator**: Verifies database availability before operations
- **ExecutionPlanAnalyzer**: Estimates query execution time, blocks if > 5 minutes
- **DatabaseComparer**: Performs safe in-database comparison with temp tables

✅ **Predefined Database Management**
- List available databases by name with descriptions
- Support for multiple databases per type (Oracle: statements, billings, transformer; MySQL: brian, prod)
- Configuration-based database references (no hardcoded connection strings)

✅ **Interactive Workflows**
- LLM asks users for source and target databases
- LLM guides query specification with WHERE clauses
- LLM helps identify key columns for comparison
- Clear error messages and safety warnings

---

## What This MCP Doesn't Do

❌ **Database Exports or File Operations**
- No database table export to CSV/Excel
- No file-based comparison tools
- Removed DBA-only export functionality

❌ **Write Operations**
- No INSERT, UPDATE, DELETE operations
- No table creation or schema modifications
- No data manipulation of any kind

❌ **Unverified Database Access**
- No arbitrary database connections
- Only predefined databases in settings.yaml can be used
- All connections validated before use

---

## When to Use This MCP

### Ideal Use Cases

1. **Production vs Test Comparison**
   - "Compare production and test billing tables to verify data consistency"
   - "Check if new transformer database has same data as old one"

2. **Cross-Database Validation**
   - "Compare Oracle statements table with MySQL brian table"
   - "Verify data migration from PostgreSQL to Oracle"

3. **Subset Comparisons**
   - "Compare only active orders between prod and test"
   - "Check customer records where country='US' in both databases"

4. **Schema Migration Verification**
   - "Compare tables after column rename migration"
   - "Verify data after database upgrade"

### Not Suitable For

- Exporting large datasets to files
- Real-time data synchronization
- Write operations or data modifications
- Arbitrary database connections without configuration

---

## How It Works

### 4-Layer Safety Architecture

```
User Request
    ↓
1. Query Validation (Read-Only Check)
    ↓
2. Database Availability Check
    ↓
3. Execution Plan Analysis (Time Estimation)
    ↓
4. In-Database Comparison (Temp Tables)
    ↓
Results Returned
```

### Interactive LLM Flow

1. **Database Selection**
   - LLM: "Which databases would you like to compare? Call `list_available_databases()` to see options."
   - User: "oracle_statements and oracle_billings"

2. **Query Specification**
   - LLM: "What query would you like to run on oracle_statements?"
   - User: "SELECT * FROM orders WHERE status = 'PENDING'"

3. **Key Column Identification**
   - LLM: "What columns should be used as join keys? (e.g., ['order_id'])"
   - User: "['order_id']"

4. **Safety Validation**
   - System validates query is read-only
   - System checks database availability
   - System analyzes execution plan

5. **Comparison Execution**
   - System creates temp tables in source database
   - System performs JOIN-based comparison
   - System returns missing/extra/different rows

---

## Available Tools

### 1. list_available_databases()
Lists all predefined databases grouped by type (Oracle/MySQL/PostgreSQL).

**Example Response:**
```json
{
  "total_databases": 7,
  "databases_by_type": {
    "oracle": ["oracle_statements", "oracle_billings", "oracle_transformer"],
    "mysql": ["mysql_brian", "mysql_prod"],
    "postgresql": ["postgres_prod", "postgres_test"]
  },
  "database_details": [
    {
      "name": "oracle_statements",
      "type": "oracle",
      "description": "Oracle Statements Database",
      "host": "oracle-prod-01.company.com"
    }
  ]
}
```

### 2. compare_database_tables()
Main comparison tool with 4-layer safety checks.

**Parameters:**
- `source_database`: Name from predefined list (e.g., 'oracle_statements')
- `target_database`: Name from predefined list
- `source_query`: SELECT query for source database
- `target_query`: SELECT query for target database
- `key_columns`: List of columns to join on (e.g., ['order_id'])
- `compare_columns`: Optional list of specific columns to compare
- `session_id`: Optional session identifier
- `override_safety`: Admin-only safety override (default: false)

**Example:**
```python
compare_database_tables(
    source_database="oracle_statements",
    target_database="oracle_billings",
    source_query="SELECT * FROM orders WHERE status = 'PENDING'",
    target_query="SELECT * FROM orders WHERE status = 'PENDING'",
    key_columns=["order_id"],
    compare_columns=["amount", "customer_id", "status"]
)
```

### 3. get_comparison_safety_info()
Returns detailed explanation of all safety mechanisms with test coverage.

---

## Safety Features

### Query Validation
- ✅ Only SELECT statements allowed
- ❌ Blocks: DROP, DELETE, UPDATE, INSERT, TRUNCATE, ALTER, CREATE
- ❌ Blocks: EXECUTE, GRANT, REVOKE
- ✅ Allows: WITH (CTEs), subqueries, JOINs

### Database Availability
- ✅ Checks database connectivity before operations
- ✅ 5-second timeout for responsiveness
- ❌ Fails fast if database unreachable

### Execution Plan Analysis
- ✅ Estimates query execution time using EXPLAIN
- ❌ Blocks queries estimated to take > 5 minutes
- ✅ Admin can override with `override_safety=true`

### In-Database Comparison
- ✅ Uses temporary tables (no data leaves database)
- ✅ Efficient JOIN-based comparison
- ✅ Automatic cleanup of temp tables

---

## Test Coverage

All safety mechanisms are thoroughly tested:

| Component | Tests | Coverage |
|-----------|-------|----------|
| QueryValidator | 33 | 93% |
| DatabaseValidator | 5 | 90% |
| ExecutionPlanAnalyzer | 16 | 94% |
| DatabaseComparer | 11 | 93% |
| **Total** | **65** | **93%** |

---

## Configuration

### Predefined Databases (settings.yaml)

```yaml
comparison_databases:
  oracle_statements:
    type: "oracle"
    description: "Oracle Statements Database"
    host: "${ORACLE_STATEMENTS_HOST}"
    port: 1521
    service_name: "${ORACLE_STATEMENTS_SERVICE}"
    user: "${ORACLE_STATEMENTS_USER}"
    password: "${ORACLE_STATEMENTS_PASSWORD}"
```

### Safety Limits

```yaml
comparison_safety:
  max_execution_time_sec: 300  # 5 minutes
  max_response_time_ms: 5000   # 5 seconds
  warn_row_count: 1000000      # Warn if > 1M rows
  admin_can_override: true     # Admin can bypass
```

---

## Next Steps

- Read [workflows.md](workflows.md) for step-by-step guides
- Read [architecture.md](architecture.md) for system internals
- Read [troubleshooting.md](troubleshooting.md) for common issues

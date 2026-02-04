# Troubleshooting Guide

Common issues and solutions for MCP Smoke Test Server.

---

## Connection Issues

### Database Unavailable

**Symptom:**
```json
{
  "error": "Database availability check failed",
  "database": "oracle_statements",
  "reason": "Connection timeout after 5000ms"
}
```

**Causes & Solutions:**

1. **Database is offline**
   - ✅ Check if database server is running
   - ✅ Contact DBA to verify database status

2. **Network connectivity**
   - ✅ Test connection: `ping oracle-host.company.com`
   - ✅ Check VPN connection if required
   - ✅ Verify firewall rules allow connection on port 1521 (Oracle) / 3306 (MySQL) / 5432 (PostgreSQL)

3. **Wrong credentials**
   - ✅ Verify environment variables in `.env` file
   - ✅ Check `settings.yaml` for correct variable references
   - ✅ Test credentials manually: `sqlplus username/password@host:port/service`

4. **Service name vs SID confusion (Oracle)**
   - ✅ Oracle uses `service_name` not `SID` in this MCP
   - ✅ Check with DBA: `SELECT name FROM v$database;`

---

## Query Validation Errors

### Dangerous Keyword Detected

**Symptom:**
```json
{
  "error": "Query validation failed",
  "reason": "Dangerous keyword detected: DELETE",
  "blocked_query": "DELETE FROM orders WHERE status = 'OLD'"
}
```

**Cause:**
- Query contains write operations (DELETE, UPDATE, INSERT, DROP, etc.)

**Solution:**
- ✅ Use only SELECT statements
- ✅ Remove modification keywords
- ✅ Use WHERE clause to filter, not DELETE

**Example Fix:**
```sql
# ❌ WRONG
DELETE FROM orders WHERE status = 'OLD'

# ✅ CORRECT
SELECT * FROM orders WHERE status != 'OLD'
```

### EXECUTE/GRANT Blocked

**Symptom:**
```json
{
  "error": "Dangerous keyword: EXECUTE"
}
```

**Cause:**
- Query attempts to execute procedures or grant permissions

**Solution:**
- ✅ Remove EXECUTE/GRANT/REVOKE keywords
- ✅ Contact admin if procedure execution is needed
- ✅ This MCP is read-only by design

---

## Execution Plan Issues

### Estimated Time Exceeds Limit

**Symptom:**
```json
{
  "warning": "Estimated execution time exceeds 5 minutes",
  "estimated_time_sec": 420,
  "query_cost": 850000,
  "recommendation": "Add WHERE clause to reduce result set"
}
```

**Causes & Solutions:**

1. **No WHERE clause on large table**
   ```sql
   # ❌ WRONG (full table scan)
   SELECT * FROM orders
   
   # ✅ CORRECT (filtered)
   SELECT * FROM orders WHERE order_date >= SYSDATE - 30
   ```

2. **Missing indexes**
   - ✅ Add WHERE clause on indexed columns
   - ✅ Contact DBA to add index if needed
   - ✅ Use primary key columns in WHERE

3. **Cartesian product (missing join)**
   ```sql
   # ❌ WRONG (Cartesian product)
   SELECT * FROM orders, customers
   
   # ✅ CORRECT (proper join)
   SELECT * FROM orders o
   JOIN customers c ON o.customer_id = c.customer_id
   ```

4. **Admin override (if legitimate)**
   ```python
   # Admin can bypass safety check
   compare_database_tables(
       ...,
       override_safety=true  # Requires admin role
   )
   ```

---

## Configuration Issues

### Environment Variable Not Set

**Symptom:**
```yaml
host: "${ORACLE_STATEMENTS_HOST}"  # Still showing placeholder
```

**Solution:**
1. ✅ Create `.env` file in `mcp_smoke/` directory
2. ✅ Copy from `.env.example`
3. ✅ Fill in actual values:
   ```env
   ORACLE_STATEMENTS_HOST=oracle-prod-01.company.com
   ORACLE_STATEMENTS_SERVICE=ORCL
   ORACLE_STATEMENTS_USER=app_user
   ORACLE_STATEMENTS_PASSWORD=SecurePass123
   ```
4. ✅ Restart MCP server

### Database Not Found

**Symptom:**
```json
{
  "error": "Database 'oracle_prod' not found in configuration",
  "available_databases": ["oracle_statements", "oracle_billings", ...]
}
```

**Solution:**
- ✅ Call `list_available_databases()` to see valid names
- ✅ Use exact names from configuration
- ✅ Check `settings.yaml` if database should be added

---

## Comparison Issues

### Key Column Not Found

**Symptom:**
```json
{
  "error": "Key column 'order_id' not found in result set",
  "available_columns": ["id", "customer_id", "amount"]
}
```

**Solution:**
- ✅ Check column name spelling (case-sensitive)
- ✅ Ensure key columns are in SELECT list
- ✅ Use `SELECT *` or explicitly list key columns

**Example:**
```python
# ❌ WRONG (key column not selected)
source_query = "SELECT amount, status FROM orders"
key_columns = ["order_id"]  # order_id not in SELECT!

# ✅ CORRECT
source_query = "SELECT order_id, amount, status FROM orders"
key_columns = ["order_id"]
```

### Different Column Names

**Symptom:**
```json
{
  "error": "Column 'cust_id' exists in source but 'customer_id' in target"
}
```

**Solution:**
- ✅ Use column aliases to match names:
```python
source_query = "SELECT cust_id as customer_id, amount FROM orders"
target_query = "SELECT customer_id, amount FROM orders"
```

### NULL Key Values

**Symptom:**
```json
{
  "warning": "Found NULL values in key column 'customer_id'",
  "null_count": 5,
  "recommendation": "Add WHERE customer_id IS NOT NULL"
}
```

**Solution:**
```sql
# Add NULL filter
SELECT * FROM orders WHERE customer_id IS NOT NULL
```

---

## Authentication Issues

### Missing API Key

**Symptom:**
```json
{
  "error": "Missing Authorization header",
  "status": 401
}
```

**Solution:**
- ✅ Add header: `Authorization: Bearer YOUR_API_KEY`
- ✅ Get API key from `.env` file or admin
- ✅ Use `ADMIN_API_KEY` or `USER_API_KEY`

### Insufficient Permissions

**Symptom:**
```json
{
  "error": "Role 'user' cannot override safety checks",
  "required_role": "admin"
}
```

**Solution:**
- ✅ Remove `override_safety=true` (only admin can use)
- ✅ Or: Request admin API key from administrator
- ✅ Optimize query instead of overriding safety

---

## Performance Issues

### Comparison Taking Too Long

**Symptom:**
- Query runs for several minutes
- No results returned

**Causes & Solutions:**

1. **Large result sets**
   - ✅ Add WHERE clause to reduce rows
   - ✅ Use date range filters
   - ✅ Compare specific subsets

2. **No indexes on join columns**
   - ✅ Request indexes from DBA
   - ✅ Use already-indexed columns (primary keys)

3. **Network latency**
   - ✅ Run comparison on database server side (this MCP does that)
   - ✅ Check network performance

### Memory Issues

**Symptom:**
```json
{
  "error": "Result set too large",
  "row_count": 5000000,
  "warning": "Consider reducing result set"
}
```

**Solution:**
- ✅ Add LIMIT/ROWNUM clause
- ✅ Reduce date range
- ✅ Use `compare_columns` to limit columns
- ✅ Compare in batches

---

## Database-Specific Issues

### Oracle: ORA-00942 (Table Not Found)

**Symptom:**
```
ORA-00942: table or view does not exist
```

**Solution:**
- ✅ Check table name spelling
- ✅ Add schema prefix: `SCHEMA_NAME.TABLE_NAME`
- ✅ Verify user has SELECT permission
- ✅ Check if table exists: `SELECT * FROM user_tables WHERE table_name = 'ORDERS';`

### MySQL: Access Denied

**Symptom:**
```
Access denied for user 'app_user'@'host'
```

**Solution:**
- ✅ Verify credentials in `.env`
- ✅ Check GRANT permissions: `SHOW GRANTS FOR 'app_user'@'%';`
- ✅ Request SELECT permission from DBA

### PostgreSQL: Permission Denied

**Symptom:**
```
permission denied for table orders
```

**Solution:**
- ✅ Grant SELECT: `GRANT SELECT ON orders TO app_user;`
- ✅ Check schema access: `GRANT USAGE ON SCHEMA public TO app_user;`

---

## Data Type Issues

### Date Format Mismatch

**Symptom:**
```json
{
  "different_values": [
    {
      "column": "order_date",
      "source_value": "2026-02-04 10:30:00",
      "target_value": "04-FEB-26"
    }
  ]
}
```

**Solution:**
- ✅ Use consistent date formats in queries:
```sql
# Oracle
SELECT TO_CHAR(order_date, 'YYYY-MM-DD') as order_date FROM orders

# MySQL
SELECT DATE_FORMAT(order_date, '%Y-%m-%d') as order_date FROM orders

# PostgreSQL
SELECT TO_CHAR(order_date, 'YYYY-MM-DD') as order_date FROM orders
```

### Decimal Precision

**Symptom:**
```json
{
  "different_values": [
    {
      "column": "amount",
      "source_value": 150.00,
      "target_value": 150.0000
    }
  ]
}
```

**Solution:**
- ✅ Round to consistent precision:
```sql
SELECT ROUND(amount, 2) as amount FROM orders
```

---

## Testing Issues

### Test Failures

**Symptom:**
```
FAILED tests/unit/test_query_validator.py::test_allow_select
```

**Solution:**
1. ✅ Ensure Python environment is configured:
   ```bash
   cd mcp_smoke
   uv sync
   ```

2. ✅ Run specific test:
   ```bash
   uv run pytest tests/unit/test_query_validator.py::test_allow_select -v
   ```

3. ✅ Check test dependencies:
   ```bash
   uv pip install pytest pytest-asyncio pytest-cov
   ```

---

## Getting Help

### Check Safety Information

```python
# Get detailed safety mechanism explanation
get_comparison_safety_info()
```

### List Available Resources

```python
# See all configured databases
list_available_databases()
```

### Read Documentation

- [overview.md](overview.md) - System capabilities
- [workflows.md](workflows.md) - Step-by-step guides
- [architecture.md](architecture.md) - How it works

### Contact Support

- Check GitHub issues: https://github.com/aviciot/mcp_smoke_test/issues
- Review test coverage: `uv run pytest --cov`
- Check logs in MCP server output

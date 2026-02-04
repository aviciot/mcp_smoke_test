# Internal Database Analysis for mcp_smoke

**Date:** February 4, 2026  
**Question:** Do we need an internal PostgreSQL database for mcp_smoke MCP?

---

## Executive Summary

**YES** - Internal PostgreSQL database is **ESSENTIAL** for mcp_smoke due to:

1. ✅ **Session Management** - Track multi-step smoke test workflows
2. ✅ **File Tracking** - Record source/target files across user sessions
3. ✅ **Comparison History** - Store test results for audit and trend analysis
4. ✅ **User Activity Logging** - Track who did what, when (compliance)
5. ✅ **Performance Analytics** - Measure test execution times, identify bottlenecks
6. ✅ **File Upload Management** - Track uploaded files, cleanup old uploads
7. ✅ **Authentication/Authorization** - Store API keys, roles, permissions
8. ✅ **Report Generation** - Store report metadata, enable re-download of old reports

---

## Why NOT Use Database? (Counter-Arguments)

### ❌ Option 1: File-Based Storage Only
**Approach:** Store everything in JSON/CSV files on disk

**Problems:**
- No concurrent access control (file locking issues)
- No query capabilities (can't search "all tests from last week")
- No relational integrity (orphaned files, lost references)
- No transaction support (partial writes if crash)
- No indexing (slow searches as data grows)
- Manual cleanup required (no automatic retention policies)

**Verdict:** ❌ Not suitable for production MCP

---

### ❌ Option 2: In-Memory Only (No Persistence)
**Approach:** Store session data in Python dictionaries

**Problems:**
- All data lost on restart/crash
- No audit trail (compliance issues)
- Can't generate historical reports
- Can't track trends over time
- Users lose test results if server restarts
- No way to resume interrupted tests

**Verdict:** ❌ Not acceptable for smoke testing (users need history)

---

### ❌ Option 3: External Logging Service (Elasticsearch, CloudWatch)
**Approach:** Send all events to external log aggregator

**Problems:**
- Adds external dependency (complexity)
- Not designed for structured session data
- Expensive for high-frequency operations
- Query performance issues for structured data
- Can't use for real-time workflow state
- No relational queries (JOINs)

**Verdict:** ❌ Complements database, doesn't replace it

---

## Why Database is ESSENTIAL

### 1. Session Management (Critical)

**Scenario:** User starts statement smoke test

```
Without DB:
User: "Start statement test"
LLM downloads source file
User: "Wait, I need to check something"
[User closes chat, comes back 1 hour later]
User: "Continue"
LLM: "❌ I don't remember what test you were doing"

With DB:
User: "Continue session stmt_20260204_143015"
LLM: [Queries DB] "✅ Found your test! Source file downloaded. Ready for target?"
```

**Database Schema:**
```sql
SELECT session_id, test_type, status, source_file_path
FROM mcp_smoke.test_sessions
WHERE status = 'active' AND client_id = 'user123'
ORDER BY created_at DESC;
```

---

### 2. File Tracking Across Sessions

**Scenario:** User uploads files via chat

```
Without DB:
User uploads: before.csv
[Server restarts]
User uploads: after.csv
LLM: "❌ I can't find before.csv anymore"

With DB:
Server restarts ✓
User: "Continue my comparison"
LLM: [Queries DB] "✅ Found before.csv (125,000 rows). Upload after.csv"
```

**Database Schema:**
```sql
SELECT file_role, file_path, row_count, file_size_mb
FROM mcp_smoke.test_files
WHERE session_id = 'upload_20260204_143015'
ORDER BY downloaded_at;
```

---

### 3. Comparison History & Audit Trail

**Scenario:** Manager asks "What tests were run last week?"

```
Without DB:
Developer: "Uh... let me search through log files..."
[Searches 50MB of text logs]
Developer: "I found... maybe 3 tests? Not sure about results"

With DB:
Developer: [Runs SQL query in 2 seconds]
SELECT session_id, test_type, match_score, mismatched_rows, created_at, client_id
FROM mcp_smoke.comparison_results
WHERE created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

Results:
- 47 tests run
- 42 passed (>95% match)
- 5 failed (<80% match)
- Average match score: 97.3%
- Most active user: avicohen (23 tests)
```

---

### 4. Performance Analytics

**Scenario:** "Why are comparisons so slow?"

```
Without DB:
No idea. Maybe check logs? Guess?

With DB:
SELECT 
    AVG(comparison_time_seconds) as avg_time,
    AVG(total_rows_source) as avg_rows,
    AVG(file_size_mb) as avg_size_mb,
    COUNT(*) as total_tests
FROM mcp_smoke.comparison_results
WHERE created_at >= NOW() - INTERVAL '30 days';

Results:
- Average time: 45 seconds
- Average rows: 250,000
- Average size: 180 MB
- Issue: 2GB files take 15 minutes (enable streaming mode!)
```

---

### 5. User Activity Logging (Compliance)

**Scenario:** Security audit requires tracking

```
Without DB:
Auditor: "Who accessed customer data last month?"
Developer: [Searches log files manually for days]

With DB:
Auditor: "Show me all users who downloaded files with 'customer' in name"

SELECT DISTINCT 
    ts.client_id,
    tf.file_path,
    tf.downloaded_at,
    ts.test_type
FROM mcp_smoke.test_files tf
JOIN mcp_smoke.test_sessions ts ON tf.session_id = ts.session_id
WHERE tf.file_path LIKE '%customer%'
  AND tf.downloaded_at >= '2026-01-01'
ORDER BY tf.downloaded_at DESC;
```

---

### 6. File Upload Management & Cleanup

**Scenario:** Upload folder grows to 500 GB

```
Without DB:
Manual cleanup script, hope you don't delete active tests

With DB:
-- Identify safe-to-delete uploads (completed + older than 7 days)
SELECT session_id, test_folder, completed_at
FROM mcp_smoke.test_sessions
WHERE status = 'completed'
  AND completed_at < NOW() - INTERVAL '7 days';

-- Automatic cleanup with audit trail
DELETE FROM mcp_smoke.test_sessions
WHERE status = 'completed' AND completed_at < NOW() - INTERVAL '30 days';
-- Cascades to test_files, comparison_results (defined in schema)
```

---

### 7. Role-Based Access Control (Authentication)

**Scenario:** Restrict DBA tools to admin users

```
Without DB:
Hardcoded API keys in code (security nightmare)

With DB:
-- Store roles, permissions, API keys
-- Tool checks: "Is this user allowed to export production DB?"

SELECT role, permissions
FROM mcp_smoke.api_keys
WHERE key_hash = SHA256('user_api_key')
  AND active = true;

-- Enable features like:
- Admins can access all tests
- Users can only see their own tests
- DBAs can export database tables
- Billing team can only run reports
```

---

### 8. Report Re-Download

**Scenario:** User lost report zip file

```
Without DB:
User: "Can I download yesterday's report again?"
LLM: "❌ Reports are only available immediately after generation"

With DB:
User: "Re-download report from session stmt_20260203_091520"
LLM: [Queries DB for zip_package_path]

SELECT zip_package_path, html_report_path
FROM mcp_smoke.comparison_results
WHERE session_id = 'stmt_20260203_091520';

LLM: "✅ [Download report.zip](file:///path/to/old/report.zip)"
```

---

## Database Design Benefits

### Relational Integrity

```
test_sessions (parent)
    ↓
test_files (children)
    ↓
comparison_results (grandchildren)
    ↓
mismatch_details (great-grandchildren)

Benefits:
- Automatic cleanup (CASCADE DELETE)
- No orphaned records
- Guaranteed data consistency
```

### Indexing for Performance

```sql
CREATE INDEX idx_test_sessions_status ON test_sessions(status);
CREATE INDEX idx_test_sessions_created ON test_sessions(created_at DESC);
CREATE INDEX idx_test_files_session ON test_files(session_id);
CREATE INDEX idx_comparison_results_session ON comparison_results(session_id);

Results:
- Query active sessions: 2ms (not 500ms)
- Find user's tests: 5ms (not 2 seconds)
- Generate reports: 10ms (not 30 seconds)
```

### Transaction Support

```python
# Atomic operation: Either all succeed or all fail
async with db_pool.acquire() as conn:
    async with conn.transaction():
        # 1. Create session
        await conn.execute("INSERT INTO test_sessions ...")
        # 2. Record source file
        await conn.execute("INSERT INTO test_files ...")
        # 3. Record target file
        await conn.execute("INSERT INTO test_files ...")
        
        # If ANY step fails, ALL are rolled back
        # No partial data, no corruption
```

---

## Comparison: mcp_db_performance Usage

The existing `mcp_db_performance` MCP uses PostgreSQL for:

1. ✅ **Query Plan Cache** - Store analyzed query plans (7-day TTL)
2. ✅ **Relationship Cache** - Store table relationships (7-day TTL)
3. ✅ **Knowledge Base** - Store table metadata, column info
4. ✅ **Performance History** - Track query performance over time
5. ✅ **User Activity** - Log who ran what query, when
6. ✅ **Authentication** - Store API keys with roles

**mcp_smoke has IDENTICAL needs:**
- Session state (like query plan cache)
- Test history (like performance history)
- File tracking (like relationship cache)
- User activity (same)
- Authentication (same)

---

## Recommended Database Setup

### Option 1: Dedicated PostgreSQL Container (RECOMMENDED)

**Pros:**
- ✅ Complete isolation from other MCPs
- ✅ Independent scaling
- ✅ Custom retention policies
- ✅ Easy backup/restore
- ✅ No schema conflicts

**Cons:**
- More containers to manage
- Slightly higher resource usage

**Implementation:**
```yaml
services:
  postgres_smoke:
    image: postgres:16-alpine
    ports:
      - "5436:5432"
    environment:
      POSTGRES_USER: mcp
      POSTGRES_PASSWORD: mcp
      POSTGRES_DB: postgres
    volumes:
      - pg_smoke_data:/var/lib/postgresql/data
      - ./postgres-init:/docker-entrypoint-initdb.d:ro
```

---

### Option 2: Shared PostgreSQL (pg_mcp) with Dedicated Schema

**Pros:**
- ✅ One PostgreSQL instance for all MCPs
- ✅ Lower resource usage
- ✅ Centralized backup
- ✅ Easier administration

**Cons:**
- Schema conflicts possible
- Coupled lifecycle (restart affects all MCPs)

**Implementation:**
```sql
-- In pg_mcp/postgres-init/015_mcp_smoke_schema.sql
CREATE SCHEMA IF NOT EXISTS mcp_smoke;
GRANT ALL PRIVILEGES ON SCHEMA mcp_smoke TO mcp;
```

---

## Recommendation

**Use Option 2: Shared PostgreSQL (pg_mcp) with dedicated `mcp_smoke` schema**

**Reasons:**
1. You already have pg_mcp infrastructure
2. Consistent with other MCPs (mcp_performance, informatica_mcp)
3. Easier management (one database to monitor)
4. Lower cost (less containers)
5. Schema isolation provides sufficient separation

**Connection Details:**
- Host: `postgres` (Docker internal) or `localhost:5436` (external)
- Database: `postgres`
- Schema: `mcp_smoke`
- User: `mcp`
- Password: `mcp`

---

## Conclusion

**VERDICT: YES, internal PostgreSQL database is ESSENTIAL**

**Without Database:**
- ❌ No session persistence
- ❌ No audit trail
- ❌ No performance analytics
- ❌ No historical reports
- ❌ No proper authentication
- ❌ Not production-ready

**With Database:**
- ✅ Reliable session management
- ✅ Complete audit trail
- ✅ Performance insights
- ✅ Report history
- ✅ Proper authentication
- ✅ Production-ready MCP

**The database is not optional - it's the foundation of a professional smoke testing system.**

---

**END OF ANALYSIS**

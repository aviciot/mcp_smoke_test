# MCP Smoke Test

**Smoke Test MCP Server** for comparing CSV files, database exports, and StorageGrid documents with comprehensive reporting.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.x-green.svg)](https://github.com/jlowin/fastmcp)

---

## 🎯 Purpose

Automated smoke testing and CSV comparison system with:
- ✅ **StorageGrid Integration** - Download documents from S3-compatible storage
- ✅ **Database Exports** - Export tables from Oracle/MySQL for comparison
- ✅ **CSV Comparison** - Intelligent comparison with mismatch detection
- ✅ **HTML Reports** - Beautiful searchable reports with summary + details
- ✅ **File Upload** - Drag-and-drop CSV/ZIP files to chat for instant comparison
- ✅ **Role-Based Access** - Admin, DBA, and User roles with API key authentication
- ✅ **Session Tracking** - Resume interrupted tests, view history

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **uv** (fast package manager): `pip install uv`
- **PostgreSQL 16** (for session/audit tracking)
- **Docker** (optional, for containerized deployment)

### Installation

```bash
# Clone repository
git clone https://github.com/aviciot/mcp_smoke_test.git
cd mcp_smoke_test

# Create virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Generate secure API keys
python -c "import secrets; print('Admin:', secrets.token_urlsafe(32))"
python -c "import secrets; print('DBA:', secrets.token_urlsafe(32))"
python -c "import secrets; print('User:', secrets.token_urlsafe(32))"

# Edit .env with your API keys and database credentials
```

### Configuration

Edit `.env`:

```bash
# Authentication (REQUIRED)
AUTH_ENABLED=true
ADMIN_API_KEY=your-secure-admin-key-here
DBA_API_KEY=your-secure-dba-key-here
USER_API_KEY=your-secure-user-key-here

# PostgreSQL Database
DB_HOST=localhost
DB_PORT=5436
DB_NAME=mcp
DB_SCHEMA=mcp_smoke
DB_USER=mcp
DB_PASSWORD=mcp

# StorageGrid (S3-compatible)
STORAGEGRID_ENDPOINT=https://storagegrid.example.com
STORAGEGRID_ACCESS_KEY=your-access-key
STORAGEGRID_SECRET_KEY=your-secret-key
STORAGEGRID_BUCKET=documents-bucket
```

### Run Server

```bash
# Development
cd server
python server.py

# Production with uvicorn
uvicorn server:app --host 0.0.0.0 --port 8200

# Docker
docker-compose up -d
```

**Server runs on:** http://localhost:8200

---

## 🔐 Authentication

### API Key-Based Authentication

All requests require `Authorization: Bearer <api_key>` header.

**3 Roles:**

| Role | Access | Use Case |
|------|--------|----------|
| **admin** | All tools | System administrators |
| **dba** | Database exports only | DBAs who need table exports |
| **user** | Smoke tests, comparisons | Regular smoke testing |

### Usage Examples

```bash
# Admin - Full access
curl -X POST http://localhost:8200/compare_csv_files \
  -H "Authorization: Bearer admin-key-here" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_001"}'

# DBA - Database export only
curl -X POST http://localhost:8200/export_database_table \
  -H "Authorization: Bearer dba-key-here" \
  -d '{"session_id": "db_001", "db_type": "oracle", "table_name": "TRANSACTIONS"}'

# User - Standard smoke tests
curl -X POST http://localhost:8200/download_storagegrid_file \
  -H "Authorization: Bearer user-key-here" \
  -d '{"session_id": "stmt_001", "file_role": "source"}'
```

---

## 📋 Features

### 1. **Statement Smoke Test** (User/Admin)

Download statement documents from StorageGrid, compare source vs. target CSV.

```python
# Tool: run_smoke_test
{
  "session_id": "stmt_20260204_001",
  "test_type": "statement",
  "storagegrid_source_file": "statements/source_jan_2026.csv",
  "storagegrid_target_file": "statements/target_jan_2026.csv",
  "ignore_columns": ["timestamp", "audit_user"],
  "report_format": "html"  # html, csv, or both
}
```

### 2. **Database Table Comparison** (DBA/Admin)

Export tables from Oracle/MySQL and compare.

```python
# Tool: export_database_table (requires admin or dba role)
{
  "session_id": "db_20260204_001",
  "db_type": "oracle",
  "connection_string": "user/pass@host:1521/ORCL",
  "table_name": "TRANSACTIONS",
  "where_clause": "transaction_date >= '2026-01-01'"
}

# Tool: compare_csv_files
{
  "session_id": "db_20260204_001",
  "ignore_columns": ["last_modified"],
  "report_format": "both"
}
```

### 3. **File Upload Comparison** (User/Admin)

Drag-and-drop CSV or ZIP files to chat.

```
User: Compare these two files [uploads source.csv, target.csv]

MCP: handle_uploaded_files → compare_csv_files → generate_report
```

### 4. **Historical Reports** (All Roles)

View and download previous test reports.

```python
# Resource: Get active sessions
sessions = get_resource("smoke://sessions/active")

# Tool: Download report
download_report(session_id="stmt_20260204_001")
```

---

## 📊 Reports

### HTML Report Structure

```
┌─────────────────────────────────────┐
│ Comparison Summary                  │
│ ✅ Match Score: 98.5%               │
│ ❌ Mismatched Rows: 45/3000         │
│ 🔍 Search: [_______]  [Apply]       │
├─────────────────────────────────────┤
│ Detailed Mismatches                 │
│ Row | Column | Source | Target      │
│ 123 | amount | 100.00 | 100.50      │
│ 456 | status | active | pending     │
│ ... (max 100 rows, configurable)    │
└─────────────────────────────────────┘

Download: comparison_report.zip
  ├── summary.html (searchable)
  ├── mismatches.csv (all rows)
  └── metadata.json (test info)
```

### Report Configuration

```yaml
# settings.yaml
smoke_test:
  report:
    format: "html"  # html, csv, or both
    max_rows_display: 100  # Max mismatches in HTML
    include_summary: true
```

---

## 🗄️ Database Schema

PostgreSQL schema: `mcp_smoke`

```sql
-- Test sessions (track all tests)
CREATE TABLE mcp_smoke.test_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    test_type VARCHAR(50),
    status VARCHAR(20),
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Test files (track all processed files)
CREATE TABLE mcp_smoke.test_files (
    file_id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) REFERENCES test_sessions(session_id),
    file_role VARCHAR(20),  -- source, target, report
    file_path TEXT,
    row_count INTEGER
);

-- Comparison results (summary metrics)
CREATE TABLE mcp_smoke.comparison_results (
    result_id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) REFERENCES test_sessions(session_id),
    total_rows INTEGER,
    matched_rows INTEGER,
    mismatched_rows INTEGER,
    match_score DECIMAL(5,2)
);

-- Mismatch details (detailed differences)
CREATE TABLE mcp_smoke.mismatch_details (
    mismatch_id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES comparison_results(result_id),
    row_number INTEGER,
    column_name VARCHAR(100),
    source_value TEXT,
    target_value TEXT
);

-- API keys (authentication)
CREATE TABLE mcp_smoke.api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(64) UNIQUE,
    name VARCHAR(100),
    role VARCHAR(50) CHECK (role IN ('admin', 'dba', 'user')),
    active BOOLEAN DEFAULT true
);

-- Audit log (track all tool calls)
CREATE TABLE mcp_smoke.audit_log (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100),
    client_id VARCHAR(100),
    client_role VARCHAR(50),
    tool_name VARCHAR(200),
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🛠️ Development

### Project Structure

```
mcp_smoke/
├── server/
│   ├── server.py              # ASGI app with middleware
│   ├── mcp_app.py             # FastMCP instance
│   ├── config.py              # Configuration loader
│   ├── auth_middleware.py     # API key authentication
│   ├── config/
│   │   └── settings.yaml      # Configuration file
│   ├── tools/
│   │   ├── tool_auth.py       # @require_roles decorator
│   │   ├── smoke_test_tools.py    # Smoke test orchestration
│   │   ├── storagegrid_tools.py   # StorageGrid downloads
│   │   ├── comparison_tools.py    # CSV comparison
│   │   ├── database_tools.py      # Database exports (DBA/Admin)
│   │   └── file_handler_tools.py  # File upload handler
│   ├── services/
│   │   ├── storagegrid_client.py  # S3 client
│   │   ├── csv_comparer.py        # Comparison engine
│   │   ├── report_generator.py    # HTML/CSV/Zip reports
│   │   ├── database_exporter.py   # Oracle/MySQL export
│   │   ├── session_manager.py     # PostgreSQL operations
│   │   └── file_handler.py        # File upload processing
│   └── utils/
│       ├── config_validator.py
│       └── request_logging.py
├── tests/                     # Test file storage
├── uploads/                   # User uploaded files
├── reports/                   # Generated reports
├── .env.example
├── requirements.txt
├── docker-compose.yml
└── README.md
```

### Running Tests

```bash
# Unit tests
pytest tests/unit

# Integration tests
pytest tests/integration

# End-to-end tests
pytest tests/e2e
```

---

## 📚 Documentation

- **[MCP_REQUIREMENTS.md](MCP_REQUIREMENTS.md)** - Complete specification (1590 lines)
- **[WORKFLOW_DETAILED.md](WORKFLOW_DETAILED.md)** - Architecture diagrams & flows
- **[INTERNAL_DB_ANALYSIS.md](INTERNAL_DB_ANALYSIS.md)** - Database justification
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Auth summary

---

## 🔗 Integration

### Claude Desktop

```json
{
  "mcpServers": {
    "mcp-smoke": {
      "url": "http://localhost:8200",
      "headers": {
        "Authorization": "Bearer your-user-api-key-here"
      }
    }
  }
}
```

### MCP Gateway (Traefik)

```yaml
# docker-compose.yml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.mcp-smoke.rule=PathPrefix(`/mcp-smoke`)"
  - "traefik.http.routers.mcp-smoke.entrypoints=web"
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'feat: Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

---

## 📞 Support

- **GitHub Issues**: https://github.com/aviciot/mcp_smoke_test/issues
- **Documentation**: See docs/ folder
- **Feedback**: Use built-in GitHub feedback tools

---

## 🎉 Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP framework
- [Starlette](https://www.starlette.io/) - ASGI framework
- [PostgreSQL](https://www.postgresql.org/) - Database
- [boto3](https://boto3.amazonaws.com/) - S3/StorageGrid client
- [pandas](https://pandas.pydata.org/) - CSV processing

Inspired by mcp_db_performance authentication system.

---

**Status:** ✅ Authentication Implemented | 🚧 Service Classes In Progress | ⏳ Tools Pending


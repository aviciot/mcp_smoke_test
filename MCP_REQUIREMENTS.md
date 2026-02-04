# MCP Requirements: Smoke Test Automation

**Version:** 1.0.0  
**Created:** February 4, 2026  
**Status:** Requirements Definition

---

## 1. MCP Identity

### Name
`mcp_smoke` - Smoke Test Automation MCP

### Description
An intelligent Model Context Protocol server for automating smoke testing workflows with interactive guidance. Supports multiple data sources (StorageGrid S3, Oracle DB, MySQL DB, CSV files) and provides advanced comparison capabilities for statements, invoices, GL documents, and database tables. Designed to guide users through complex ETL validation workflows with contextual prompts and real-time progress updates.

### Purpose & Value Proposition
- **Problem:** Manual smoke testing is time-consuming, error-prone, and requires remembering multiple configuration details
- **Solution:** Interactive LLM-guided testing with preset configurations, automatic file management, and intelligent comparison
- **Value:** Reduces testing time by 80%, eliminates configuration errors, provides detailed mismatch reports, handles large files (2GB+)

### Version
1.0.0

---

## 2. Architecture & Design Principles

### Object-Oriented Design (OOP Approach)

All smoke test operations utilize dedicated service classes for maintainability, testability, and reusability:

#### Class: StorageGridClient
**Location:** `server/services/storagegrid_client.py`

**Purpose:** Encapsulate all StorageGrid S3 operations

**Design:**
```python
class StorageGridClient:
    """
    Manages StorageGrid S3 connections and file operations
    """
    
    def __init__(self, config: Dict[str, Any], bucket: str, doc_type: str):
        self.endpoint_url = config["endpoint_url"]
        self.bucket = bucket
        self.doc_type = doc_type
        self.s3_client = self._create_s3_client(config)
    
    def generate_key(self, **metadata) -> str:
        """Generate S3 key based on document type and metadata"""
        
    def download_file(self, download_path: str, **metadata) -> DownloadResult:
        """Download file from StorageGrid and return metadata"""
        
    def list_files(self, prefix: str) -> List[str]:
        """List files matching prefix"""
        
    def get_file_metadata(self, key: str) -> FileMetadata:
        """Get file metadata without downloading"""
```

**Benefits:**
- Single responsibility (S3 operations only)
- Testable with mocked S3 client
- Reusable across different tools
- Configuration encapsulated

---

#### Class: CSVComparer
**Location:** `server/services/csv_comparer.py`

**Purpose:** Handle all CSV comparison logic with streaming support

**Design:**
```python
class CSVComparer:
    """
    Performs CSV file comparisons with configurable options
    """
    
    def __init__(self, config: ComparisonConfig):
        self.config = config
        self.streaming_threshold = config.streaming_threshold_mb
        self.chunk_size = config.chunk_size
    
    def compare(self, source_path: str, target_path: str, 
                options: ComparisonOptions) -> ComparisonResult:
        """
        Main comparison method - automatically chooses streaming or in-memory
        """
        
    def _compare_in_memory(self, source_df, target_df) -> ComparisonResult:
        """Fast comparison for small files"""
        
    def _compare_streaming(self, source_path, target_path) -> ComparisonResult:
        """Memory-efficient comparison for large files"""
        
    def _apply_filters(self, df: pd.DataFrame, options: ComparisonOptions):
        """Apply ignore_columns, sorting, etc."""
        
    def calculate_match_score(self, result: ComparisonResult) -> float:
        """Calculate match percentage (0-100)"""
```

**Data Classes:**
```python
@dataclass
class ComparisonConfig:
    chunk_size: int = 10000
    streaming_threshold_mb: int = 100
    case_sensitive: bool = True
    trim_whitespace: bool = True

@dataclass
class ComparisonOptions:
    ignore_columns: List[str] = field(default_factory=list)
    ignore_columns_source: List[str] = field(default_factory=list)
    ignore_columns_target: List[str] = field(default_factory=list)
    sort_by_columns: Optional[List[str]] = None
    max_mismatches_report: int = 5000

@dataclass
class ComparisonResult:
    match_score: float
    total_rows_source: int
    total_rows_target: int
    matched_rows: int
    mismatched_rows: int
    source_only_rows: int
    target_only_rows: int
    mismatch_details: List[MismatchRow]
    comparison_time: float
    memory_used_mb: float
```

---

#### Class: ReportGenerator
**Location:** `server/services/report_generator.py`

**Purpose:** Generate comparison reports in multiple formats (CSV, HTML, both)

**Design:**
```python
class ReportGenerator:
    """
    Generates comparison reports in configurable formats
    """
    
    def __init__(self, config: ReportConfig):
        self.config = config
        self.jinja_env = self._setup_jinja()
    
    def generate_report(self, comparison_result: ComparisonResult,
                       session_info: SessionInfo) -> ReportOutput:
        """
        Generate report(s) based on configuration
        Returns paths to generated files
        """
        
    def _generate_html(self, result: ComparisonResult) -> str:
        """Generate interactive HTML report"""
        
    def _generate_csv(self, result: ComparisonResult) -> str:
        """Generate simple CSV report of mismatches"""
        
    def _create_zip_package(self, files: List[str]) -> str:
        """Package all report files into zip"""
        
    def _calculate_quality_rating(self, match_score: float) -> str:
        """Determine Pass/Warning/Fail based on thresholds"""

@dataclass
class ReportConfig:
    formats: List[str] = field(default_factory=lambda: ["html"])  # ["html", "csv", "both"]
    max_rows_in_report: int = 5000
    rows_per_page: int = 100
    include_charts: bool = True
    generate_zip: bool = True
    match_score_thresholds: Dict[str, float] = field(default_factory=dict)

@dataclass
class ReportOutput:
    html_path: Optional[str] = None
    csv_path: Optional[str] = None
    zip_path: Optional[str] = None
    summary_text: str = ""
```

---

#### Class: DatabaseExporter
**Location:** `server/services/database_exporter.py`

**Purpose:** Export database tables to CSV for comparison

**Design:**
```python
class DatabaseExporter:
    """
    Exports database tables (Oracle/MySQL) to CSV
    """
    
    def __init__(self, db_type: str, connection_config: Dict[str, Any]):
        self.db_type = db_type
        self.connection_config = connection_config
        self.pool = None
    
    async def connect(self):
        """Establish connection pool"""
        
    async def export_table(self, table_name: str, 
                          export_path: str,
                          options: ExportOptions) -> ExportResult:
        """Export table to CSV with streaming"""
        
    async def execute_query(self, query: str, export_path: str) -> ExportResult:
        """Export custom query results to CSV"""
        
    async def close(self):
        """Close connection pool"""

@dataclass
class ExportOptions:
    where_clause: Optional[str] = None
    order_by: Optional[str] = None
    limit: Optional[int] = None
    chunk_size: int = 10000

@dataclass
class ExportResult:
    file_path: str
    row_count: int
    column_count: int
    columns: List[str]
    file_size_mb: float
    export_time: float
```

---

#### Class: SessionManager
**Location:** `server/services/session_manager.py`

**Purpose:** Manage test sessions and database operations

**Design:**
```python
class SessionManager:
    """
    Manages smoke test sessions and persists to PostgreSQL
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def create_session(self, test_type: str, preset: str) -> TestSession:
        """Create new test session with unique ID and folder"""
        
    async def get_session(self, session_id: str) -> Optional[TestSession]:
        """Retrieve session by ID"""
        
    async def update_session_status(self, session_id: str, status: str):
        """Update session status (active/completed/failed)"""
        
    async def add_file_to_session(self, session_id: str, 
                                  file_info: FileInfo) -> int:
        """Record file in database, return file_id"""
        
    async def save_comparison_result(self, session_id: str,
                                     result: ComparisonResult,
                                     report: ReportOutput):
        """Save comparison result to database"""
        
    async def list_active_sessions(self) -> List[TestSession]:
        """Get all active sessions"""

@dataclass
class TestSession:
    session_id: str
    test_type: str
    preset: str
    test_folder: str
    status: str
    created_at: datetime
    source_file: Optional[FileInfo] = None
    target_file: Optional[FileInfo] = None
```

---

#### Class: FileHandler
**Location:** `server/services/file_handler.py`

**Purpose:** Handle user-uploaded files (CSV/ZIP) with validation and extraction

**Design:**
```python
class FileHandler:
    """
    Processes uploaded files from chat interface
    """
    
    def __init__(self, config: FileUploadConfig):
        self.config = config
        self.upload_folder = config.upload_folder
        self.allowed_extensions = config.allowed_extensions
        self.max_size_mb = config.max_upload_size_mb
    
    async def handle_upload(self, file: UploadFile, 
                           session_id: Optional[str] = None) -> FileUploadResult:
        """Process uploaded file and save to session folder"""
        
    def validate_file(self, file: UploadFile) -> ValidationResult:
        """Validate file type and size"""
        
    async def extract_zip(self, zip_path: str, extract_to: str) -> List[str]:
        """Extract CSV files from ZIP archive"""
        
    async def analyze_csv(self, csv_path: str) -> CSVMetadata:
        """Analyze CSV structure (rows, columns, size)"""
        
    async def cleanup_old_uploads(self, retention_hours: int = 24):
        """Remove uploaded files older than retention period"""

@dataclass
class FileUploadConfig:
    upload_folder: str
    allowed_extensions: List[str]
    max_upload_size_mb: int
    auto_extract_zip: bool
    validate_csv_on_upload: bool

@dataclass
class FileUploadResult:
    status: str  # success, error
    session_id: str
    file_path: str
    file_info: CSVMetadata
    extracted_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

@dataclass
class CSVMetadata:
    file_name: str
    file_size_mb: float
    row_count: int
    column_count: int
    columns: List[str]
    has_header: bool
```

**Features:**
- File type validation (CSV/ZIP only)
- Size limit enforcement (default 5GB)
- Automatic ZIP extraction
- CSV structure analysis
- Temporary file cleanup
- Async file operations (aiofiles)

---

### Design Principles

1. **Separation of Concerns:** Each class has single responsibility
2. **Dependency Injection:** Classes receive configuration, not hardcoded values
3. **Async Support:** Database and HTTP operations are async
4. **Type Safety:** Use dataclasses and type hints throughout
5. **Testability:** Classes can be mocked and tested independently
6. **Reusability:** Services used by multiple tools
7. **Configuration-Driven:** Behavior controlled by settings.yaml and tool parameters

---

## 3. Core Capabilities

### Primary Use Cases

#### Use Case 1: Statement Smoke Test (StorageGrid)
**Trigger:** User says "Start statement smoke test" or "Test statement files"

**Flow:**
1. LLM asks for preset selection (from settings.yaml: production/staging/dev)
2. LLM requests document parameters (contract_number, payment_date, transform_subtype)
3. MCP downloads source file from StorageGrid
4. MCP creates unique test folder (e.g., `tests/statement_2026-02-04_14-30-15/`)
5. MCP reports file details (size, rows, location, key name)
6. User runs ETL process (file gets overwritten in StorageGrid)
7. LLM asks: "Ready to download target file?" with options (same location/new location)
8. MCP downloads target file (same key or user-specified location)
9. MCP validates both files are ready for comparison
10. MCP performs CSV comparison with configurable options
11. MCP generates detailed mismatch report

#### Use Case 2: Invoice Smoke Test (StorageGrid)
**Trigger:** User says "Start invoice smoke test" or "Test invoice files"

**Flow:** Similar to statement test but with invoice-specific parameters (contract_number, partner_contract, currency, payment_date)

#### Use Case 3: GL Document Smoke Test (StorageGrid)
**Trigger:** User says "Start GL smoke test" or "Test general ledger files"

**Flow:** Similar to statement test but with GL-specific parameters (gl_document_type, financial_institution, gl_posting_date)

#### Use Case 4: Database Table Comparison
**Trigger:** User says "Compare database tables" or "Start table smoke test"

**Flow:**
1. LLM asks for source database (Oracle/MySQL) and preset
2. LLM asks for table name and optional query filters
3. MCP exports source table to CSV in test folder
4. User runs ETL process
5. LLM asks for target database and table
6. MCP exports target table to CSV
7. MCP performs comparison
8. MCP generates mismatch report

#### Use Case 5: CSV File Comparison (Local/Zip)
**Trigger:** User says "Compare CSV files" or "Test CSV comparison"

**Flow:**
1. LLM asks for source file path
2. If zip file, MCP extracts to test folder
3. LLM asks for target file path
4. If zip file, MCP extracts to test folder
5. MCP validates CSV files
6. LLM asks for comparison options (ignore columns, sort columns, streaming mode)
7. MCP performs comparison
8. MCP generates mismatch report

#### Use Case 6: File Upload and Comparison
**Trigger:** User uploads files directly to chat (CSV or ZIP)

**Flow:**
1. User drags and drops files into chat or uses file upload button
2. LLM detects file attachments and calls `handle_uploaded_files`
3. MCP receives files, saves to temporary session folder
4. If ZIP files, automatically extracts CSV contents
5. LLM asks: "I received [source.csv]. Upload the target file or specify a path?"
6. User uploads second file or provides path
7. MCP validates both files are CSV format
8. LLM asks for comparison options
9. MCP performs comparison using CSVComparer
10. MCP generates report and returns download link

**Benefits:**
- No need to specify file paths
- Works with files from any location (local machine, network drives)
- Supports drag-and-drop for quick comparisons
- Automatic zip extraction

### Secondary Use Cases

- **List Available Presets:** Show configured environments and their details
- **Validate Configuration:** Check StorageGrid connectivity, database connections
- **Archive Test Results:** Move completed test folders to archive with metadata
- **Generate Test Summary Report:** Aggregate results from multiple test runs
- **Extract Zip Files:** Extract specific files from zip archives for inspection
- **Preview File:** Show first N rows of CSV file before comparison

---

## 3. External Systems & Integrations

### StorageGrid (S3-Compatible Object Storage)

**Connection Type:** boto3 S3 client  
**Protocol:** HTTPS  
**Authentication:** Access Key ID + Secret Access Key  
**Purpose:** Download source/target files for statements, invoices, GL documents

**Configuration Requirements:**
```yaml
storagegrid:
  presets:
    production:
      endpoint_url: "https://sg-gw01.prod.bos.credorax.com:8082"
      aws_access_key_id: "${STORAGEGRID_PROD_ACCESS_KEY}"
      aws_secret_access_key: "${STORAGEGRID_PROD_SECRET_KEY}"
      verify: false
      max_pool_connections: 10
      buckets:
        statements: "credorax-statements"
        invoices: "credorax-invoices"
        gl_documents: "credorax-gl"
    
    staging:
      endpoint_url: "https://sg-gw01.staging.bos.credorax.com:8082"
      aws_access_key_id: "${STORAGEGRID_STAGING_ACCESS_KEY}"
      aws_secret_access_key: "${STORAGEGRID_STAGING_SECRET_KEY}"
      verify: false
      max_pool_connections: 10
      buckets:
        statements: "credorax-statements-staging"
        invoices: "credorax-invoices-staging"
        gl_documents: "credorax-gl-staging"
    
    development:
      endpoint_url: "https://sg-gw01.dev1.bos.credorax.com:8082"
      aws_access_key_id: "L82LRUAHFB96RQHIRBIH"
      aws_secret_access_key: "3bm1zIPaIHU1GoPC3g2+oky8J5PYt9Wvu5V1lNig"
      verify: false
      max_pool_connections: 10
      buckets:
        statements: "credorax-statements-dev"
        invoices: "credorax-invoices-dev"
        gl_documents: "credorax-gl-dev"
```

**Error Handling:**
- Connection timeout → Retry 3 times with exponential backoff
- 404 Not Found → Clear error message with expected key format
- 403 Forbidden → Check credentials and bucket permissions
- SSL verification errors → Document verify=false requirement

### Oracle Database

**Connection Type:** oracledb (python-oracledb)  
**Protocol:** TCP  
**Authentication:** Username/Password  
**Purpose:** Export tables for comparison testing

**Configuration Requirements:**
```yaml
oracle:
  presets:
    production:
      host: "${ORACLE_PROD_HOST}"
      port: 1521
      service_name: "${ORACLE_PROD_SERVICE}"
      username: "${ORACLE_PROD_USER}"
      password: "${ORACLE_PROD_PASSWORD}"
      thick_mode: false
    
    staging:
      host: "${ORACLE_STAGING_HOST}"
      port: 1521
      service_name: "${ORACLE_STAGING_SERVICE}"
      username: "${ORACLE_STAGING_USER}"
      password: "${ORACLE_STAGING_PASSWORD}"
      thick_mode: false
```

**Query Requirements:**
- Support parameterized queries for filtering
- Export to CSV with configurable chunk size (10,000 rows)
- Handle large result sets (streaming export)
- Include column headers in CSV output

### MySQL Database

**Connection Type:** aiomysql  
**Protocol:** TCP  
**Authentication:** Username/Password  
**Purpose:** Export tables for comparison testing

**Configuration Requirements:**
```yaml
mysql:
  presets:
    production:
      host: "${MYSQL_PROD_HOST}"
      port: 3306
      database: "${MYSQL_PROD_DB}"
      user: "${MYSQL_PROD_USER}"
      password: "${MYSQL_PROD_PASSWORD}"
    
    staging:
      host: "${MYSQL_STAGING_HOST}"
      port: 3306
      database: "${MYSQL_STAGING_DB}"
      user: "${MYSQL_STAGING_USER}"
      password: "${MYSQL_STAGING_PASSWORD}"
```

---

## 4. Tools Specification

### 🔧 Standard Tools (Included in All MCPs)

#### GitHub Feedback System
**File:** `server/tools/mcp_feedback.py`

**Purpose:** Allow users to report bugs, request features, and suggest improvements via interactive workflow that creates GitHub issues.

**Tools Included:**
- `report_mcp_issue_interactive` - Interactive bug/feature/improvement reporting
- Quality scoring and auto-improvement suggestions
- GitHub issue creation with structured templates

**Configuration:**
```yaml
feedback:
  enabled: true
  repo: "your-org/mcp_smoke"
  maintainer: "your-team"
  quality:
    enabled: true
    auto_improve: true
    auto_improve_threshold: 4.0
```

**Environment Variables:**
- `GITHUB_TOKEN` - GitHub personal access token for issue creation
- `GITHUB_REPO` - Repository in format "owner/repo"

**Note:** This is a standard tool copied from template_mcp and should be included in every MCP unless explicitly excluded by user.

---

### 🔧 Smoke Test Specific Tools

### 🔧 Tool 1: start_smoke_test

**Name:** `start_smoke_test`

**Description:**
```
Start an interactive smoke test workflow for statements, invoices, GL documents, or database tables.

**Use when:** User says "start smoke test", "begin statement test", "test invoice files", etc.

**Parameters:**
  - test_type: Type of smoke test (statement/invoice/gl/database_table/csv_comparison)
  - preset: Configuration preset name (production/staging/development)
  - interactive: Whether to prompt for parameters (default: true)

**Returns:** Dictionary with test session ID, test folder path, and next steps for user

**Workflow:**
  1. Creates unique test folder: tests/{test_type}_{timestamp}/
  2. Loads preset configuration
  3. Returns session details for tracking
  4. LLM uses session_id for subsequent tool calls
```

**Priority:** High (Core workflow initiator)

**Parameters:**
- `test_type` (string, required): "statement" | "invoice" | "gl" | "database_table" | "csv_comparison"
- `preset` (string, required): Preset name from settings.yaml
- `interactive` (boolean, optional, default=true): Enable interactive prompting mode

**Error Handling:**
- Invalid test_type → List available types
- Unknown preset → List available presets
- Test folder creation failure → Check permissions

---

### 🔧 Tool 2: download_storagegrid_file

**Name:** `download_storagegrid_file`

**Description:**
```
Download a file from StorageGrid S3 using document-specific key generation.

**Use when:** User confirms parameters for source/target file download in smoke test workflow.

**Parameters:**
  - session_id: Active smoke test session ID
  - file_role: Whether this is 'source' or 'target' file
  - doc_type: Document type (statement/invoice/gl)
  - contract_number: Contract number (required for statement/invoice)
  - payment_date: Payment date in YYYY-MM-DD format (required for statement/invoice)
  - transform_subtype: Transform subtype like 'CREDORAX' (required for statement/invoice)
  - partner_contract: Partner contract (required for invoice)
  - currency: Currency code (required for invoice)
  - gl_document_type: GL document type (required for gl)
  - financial_institution: Financial institution code (required for gl)
  - gl_posting_date: Posting date in YYYY-MM-DD format (required for gl)
  - file_extension: File extension (default: 'CSV')
  - preset: StorageGrid preset (optional, uses session preset if not specified)

**Returns:** Dictionary with:
  - download_status: success/failure
  - file_path: Local path where file was saved
  - file_size_bytes: Size of downloaded file
  - file_size_mb: Human-readable size
  - row_count: Number of rows in CSV (excluding header)
  - column_count: Number of columns
  - s3_key: The S3 key that was used
  - download_time_seconds: Time taken to download

**Key Generation Logic:**
  Statement: {prefix}.{contract_number}.{payment_date}.{transform_subtype}.{extension}
  Invoice: {prefix}.{contract_number}.{partner_contract}.{currency}.{payment_date}.{transform_subtype}.{extension}
  GL: {gl_document_type}.{financial_institution}.{gl_posting_date}.{extension}
```

**Priority:** High (Core workflow step)

**Parameters:** (See description for full parameter list)

**Error Handling:**
- File not found (404) → Show expected key format, suggest checking parameters
- Connection timeout → Retry with exponential backoff (3 attempts)
- Invalid session_id → List active sessions
- CSV parsing error → Show file preview, suggest checking format

---

### 🔧 Tool 3: compare_csv_files

**Name:** `compare_csv_files`

**Description:**
```
Perform advanced comparison between two CSV files with support for large files (2GB+), column filtering, real-time mismatch reporting, and HTML report generation.

**Use when:** User confirms both source and target files are ready for comparison.

**Parameters:**
  - session_id: Active smoke test session ID
  - source_file: Path to source CSV file (optional if session has source)
  - target_file: Path to target CSV file (optional if session has target)
  - ignore_columns: List of column names to exclude from comparison (applies to both files)
  - ignore_columns_source: List of columns to ignore only in source file
  - ignore_columns_target: List of columns to ignore only in target file
  - sort_by_columns: List of columns to sort by before comparison (default: all remaining columns)
  - case_sensitive: Whether string comparison is case-sensitive (default: true)
  - trim_whitespace: Whether to trim leading/trailing whitespace (default: true)
  - streaming_mode: Use memory-efficient streaming for large files (default: auto-detect if > 100MB)
  - chunk_size: Number of rows to process per chunk in streaming mode (default: 10000)
  - report_mismatches_live: Report mismatches as they're found (default: true)
  - max_mismatches_report: Maximum mismatches to include in HTML report (default: from settings.yaml)
  - generate_html_report: Create interactive HTML report with search (default: true)
  - generate_zip: Package report with CSV diffs as zip file (default: true)

**Returns:** Dictionary with:
  - comparison_status: success/failure
  - match_score: Percentage match (0-100)
  - quality_rating: Pass/Warning/Fail based on score
  - total_rows_source: Row count in source
  - total_rows_target: Row count in target
  - matched_rows: Number of matching rows
  - mismatched_rows: Number of rows with differences
  - source_only_rows: Rows only in source
  - target_only_rows: Rows only in target
  - columns_compared: List of column names that were compared
  - mismatch_summary: Dictionary of column → mismatch_count
  - html_report_path: Path to interactive HTML report (if generated)
  - zip_package_path: Path to zip file containing HTML + CSV diffs (if generated)
  - summary_text: Human-readable summary for LLM to return to user
  - comparison_time_seconds: Time taken
  - memory_used_mb: Peak memory usage

**LLM Response Pattern:**
  LLM should return ONLY the summary_text to user and provide download link:
  "✅ Comparison complete! Match score: 98.5%
  
  Found 45 mismatches across 3 columns (see details in report).
  
  📦 Download complete report: [comparison_report_20260204_143015.zip](file:///path/to/report.zip)
  
  The zip contains:
  - Interactive HTML report with search and filtering
  - Detailed CSV of all mismatches
  - Source/target file metadata"

**Streaming Mode:**
  - Automatically enabled for files > 100MB
  - Processes files in chunks to handle 2GB+ files
  - Sorts chunks individually then merges
  - Uses temporary files for intermediate results

**Live Mismatch Updates:**
  - When enabled, tool returns partial results periodically
  - LLM can update user: "Found 15 mismatches in first 50,000 rows..."
  - Continues processing in background

**HTML Report Structure:**
  Section 1 - High-Level Summary:
  - Match score with color-coded indicator (green ≥95%, yellow 80-95%, red <80%)
  - Quality rating (Pass/Warning/Fail)
  - Executive summary explaining differences
  - Key statistics (total rows, matched, mismatched, source-only, target-only)
  - Per-column mismatch breakdown with charts
  - Test metadata (session ID, files, timestamps)
  
  Section 2 - Detailed Mismatches:
  - Interactive table with search/filter capabilities
  - Sortable by row number, column, source value, target value
  - Highlighting of differences
  - Pagination (configurable rows per page from settings.yaml)
  - Export filtered results as CSV
  - Limited to max_mismatches_report rows (configurable in settings.yaml)
  
  Technical Features:
  - Responsive design (mobile-friendly)
  - Client-side search (JavaScript, no server needed)
  - Collapsible sections
  - Copy to clipboard functionality
  - Dark/light mode toggle
```

**Priority:** High (Core comparison engine)

**Parameters:** (See description for full parameter list)

**Error Handling:**
- Files not found → Verify session files or provided paths
- CSV format mismatch → Report column differences clearly
- Out of memory → Suggest enabling streaming_mode
- Empty files → Report as error with clear message

---

### 🔧 Tool 4: export_database_table

**Name:** `export_database_table`

**Description:**
```
Export a database table (Oracle or MySQL) to CSV format for comparison testing.

**Use when:** User wants to compare database tables or export table data for smoke testing.

**Parameters:**
  - session_id: Active smoke test session ID
  - db_type: Database type ('oracle' or 'mysql')
  - preset: Database preset name from settings.yaml
  - table_name: Full table name (with schema if needed)
  - query: Optional custom SQL query (overrides table_name)
  - where_clause: Optional WHERE clause for filtering
  - order_by: Optional ORDER BY clause
  - limit: Optional row limit for testing
  - file_role: 'source' or 'target' for comparison workflow
  - export_path: Optional custom export path (default: session test folder)

**Returns:** Dictionary with:
  - export_status: success/failure
  - file_path: Path to exported CSV
  - row_count: Number of rows exported
  - column_count: Number of columns
  - columns: List of column names
  - file_size_mb: File size
  - export_time_seconds: Time taken
  - query_executed: The actual SQL query that was run

**SQL Generation:**
  - If query provided: Use as-is
  - If table_name + where_clause: SELECT * FROM {table} WHERE {where}
  - If table_name only: SELECT * FROM {table}
  - Always adds ORDER BY if specified
  - Always adds LIMIT if specified

**Streaming Export:**
  - Fetches rows in chunks (10,000 default)
  - Writes directly to CSV to minimize memory
  - Shows progress for large exports
```

**Priority:** High (Database integration)

**Parameters:** (See description for full parameter list)

**Error Handling:**
- Connection failure → Check preset configuration and credentials
- Table not found → List available tables
- SQL syntax error → Show query, suggest corrections
- Permission denied → Check database user privileges

---

### 🔧 Tool 5: extract_zip_file

**Name:** `extract_zip_file`

**Description:**
```
Extract files from a zip archive to the test folder.

**Use when:** User provides a zip file path for CSV comparison.

**Parameters:**
  - session_id: Active smoke test session ID (optional, creates temp folder if not provided)
  - zip_file_path: Path to zip file
  - extract_to: Optional extraction directory (default: session test folder)
  - file_pattern: Optional glob pattern to extract specific files (default: *.csv)
  - password: Optional password for encrypted zips

**Returns:** Dictionary with:
  - extraction_status: success/failure
  - extracted_files: List of extracted file paths
  - file_count: Number of files extracted
  - extract_path: Directory where files were extracted
  - zip_size_mb: Original zip file size
  - extracted_size_mb: Total size of extracted files
```

**Priority:** Medium (Supporting utility)

**Parameters:** (See description for full parameter list)

---

### 🔧 Tool 6: list_presets

**Name:** `list_presets`

**Description:**
```
List all available configuration presets for StorageGrid, Oracle, and MySQL.

**Use when:** User asks "what presets are available" or "show configurations".

**Parameters:**
  - system: Optional filter (storagegrid/oracle/mysql/all) (default: all)

**Returns:** Dictionary with preset details including environment names, endpoints, and purpose
```

**Priority:** Low (Informational)

---

### 🔧 Tool 7: validate_connections

**Name:** `validate_connections`

**Description:**
```
Test connectivity to StorageGrid, Oracle, and MySQL using configured presets.

**Use when:** User asks "test connections" or "validate configuration".

**Parameters:**
  - preset: Preset name to test (optional, tests all if not specified)
  - system: System type to test (storagegrid/oracle/mysql/all) (default: all)

**Returns:** Dictionary with connection test results for each system
```

**Priority:** Low (Diagnostic)

---

### 🔧 Tool 8: get_test_status

**Name:** `get_test_status`

**Description:**
```
Get the current status of an active smoke test session.

**Use when:** User asks "what's the test status" or LLM needs to check session state.

**Parameters:**
  - session_id: Test session ID

**Returns:** Dictionary with:
  - session_id
  - test_type
  - test_folder
  - created_at
  - current_step: Current workflow step
  - source_file: Source file details (if downloaded)
  - target_file: Target file details (if downloaded)
  - comparison_result: Comparison result (if completed)
  - status: active/completed/failed
```

**Priority:** Medium (Workflow tracking)

---

### 🔧 Tool 9: preview_csv_file

**Name:** `preview_csv_file`

**Description:**
```
Show the first N rows of a CSV file for quick inspection.

**Use when:** User asks "show me the file" or "preview the data".

**Parameters:**
  - file_path: Path to CSV file
  - num_rows: Number of rows to show (default: 10, max: 100)
  - show_columns: Whether to show column information (default: true)

**Returns:** Dictionary with column names, data types, sample rows, and file statistics
```

**Priority:** Low (Utility)

---

### 🔧 Tool 10: archive_test_results

**Name:** `archive_test_results`

**Description:**
```
Move completed test folder to archive with metadata for historical tracking.

**Use when:** User says "archive this test" or "save test results".

**Parameters:**
  - session_id: Test session ID
  - notes: Optional notes about the test (default: "")
  - archive_location: Optional custom archive path (default: tests/archive/)

**Returns:** Dictionary with archive path and metadata
```

**Priority:** Low (Housekeeping)

---

### 🔧 Tool 11: handle_uploaded_files

**Name:** `handle_uploaded_files`

**Description:**
```
Handle files uploaded directly by user to the chat interface (CSV or ZIP files).

**Use when:** User uploads files via drag-and-drop or file upload button in chat.

**Parameters:**
  - files: List of uploaded file objects with metadata
  - session_id: Optional existing session ID (creates new if not provided)
  - file_role: Role of uploaded files ('source', 'target', or 'auto' for automatic detection)
  - auto_extract_zip: Whether to automatically extract ZIP files (default: true)
  - comparison_options: Optional comparison options if both files uploaded

**Returns:** Dictionary with:
  - session_id: Test session ID (created or existing)
  - files_processed: List of processed file information
  - extracted_files: List of files extracted from ZIPs (if any)
  - ready_for_comparison: Boolean indicating if both source and target are ready
  - next_action: Guidance for user on what to do next

**File Processing:**
  1. Validate file types (CSV or ZIP only)
  2. Save uploaded files to session folder
  3. If ZIP, extract all CSV files
  4. Analyze CSV structure (rows, columns, size)
  5. Determine file role (source/target) based on upload order
  6. If both files present, offer immediate comparison

**Workflow Examples:**
  
  Single file uploaded:
  - User uploads 'transactions.csv'
  - LLM: "I've received transactions.csv (250,000 rows). Upload the target file to compare."
  
  ZIP file uploaded:
  - User uploads 'data_export.zip'
  - Tool extracts: statement.csv, invoice.csv
  - LLM: "I extracted 2 CSV files. Which one do you want to use as source?"
  
  Both files uploaded at once:
  - User uploads 'before.csv' and 'after.csv'
  - LLM: "I have both files. Compare them now? (Ignore any columns?)"
```

**Priority:** High (Core feature for user convenience)

**Error Handling:**
- Invalid file type → "Only CSV and ZIP files are supported"
- ZIP with no CSVs → "ZIP file contains no CSV files"
- Files too large (>5GB) → "File exceeds maximum size limit"
- Corrupted ZIP → "Cannot extract ZIP file, it may be corrupted"

---

## 5. Resources

### Resource 1: Active Test Sessions

**URI Pattern:** `smoke-test://sessions/{session_id}`

**Description:** Provides metadata about active and recent test sessions

**MIME Type:** application/json

**Content Example:**
```json
{
  "session_id": "stmt_20260204_143015",
  "test_type": "statement",
  "preset": "development",
  "status": "awaiting_target",
  "source_file": {
    "path": "tests/statement_2026-02-04_14-30-15/source.csv",
    "size_mb": 12.5,
    "rows": 45320
  }
}
```

---

### Resource 2: Test Configuration Presets

**URI Pattern:** `smoke-test://presets/{system}/{preset_name}`

**Description:** Provides details about configured presets (non-sensitive info only)

**MIME Type:** application/json

---

### Resource 3: File Upload Handler

**URI Pattern:** `smoke-test://upload`

**Description:** Accepts file uploads from chat interface

**MIME Types Accepted:** 
- `text/csv` (CSV files)
- `application/zip` (ZIP archives containing CSV files)
- `application/x-zip-compressed` (ZIP archives)

**HTTP Method:** POST

**Request Format:**
```
POST /upload
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="file"; filename="source.csv"
Content-Type: text/csv

[CSV data]
--boundary
Content-Disposition: form-data; name="session_id"

stmt_20260204_143015
--boundary--
```

**Response Format:**
```json
{
  "status": "success",
  "session_id": "upload_20260204_143015",
  "file_saved": "tests/upload_20260204_143015/source.csv",
  "file_info": {
    "name": "source.csv",
    "size_mb": 5.2,
    "rows": 12500,
    "columns": 15
  },
  "ready_for_comparison": false,
  "next_action": "Upload target file or specify path"
}
```

**Usage in Chat:**
- User drags file into chat window
- LLM calls this resource endpoint
- File is processed and saved
- LLM informs user of file details

---

## 6. Prompts

### Prompt 1: start_statement_test

**Name:** `start_statement_test`

**Description:** Interactive wizard to guide user through statement smoke test

**Arguments:**
- `preset` (optional): Pre-select environment

**Workflow:**
1. "Which environment? (production/staging/development)"
2. "Contract number?"
3. "Payment date (YYYY-MM-DD)?"
4. "Transform subtype (e.g., CREDORAX)?"
5. Execute download_storagegrid_file
6. "File downloaded! Run your ETL process. Reply 'continue' when ready."
7. "Download target from same location or specify new location?"
8. Execute download_storagegrid_file for target
9. "Ready to compare. Any columns to ignore?"
10. Execute compare_csv_files
11. Show results

---

### Prompt 2: start_database_comparison

**Name:** `start_database_comparison`

**Description:** Interactive wizard for database table comparison

---

## 7. Database Requirements

### Database Required?
**YES** - For session tracking, test history, and comparison result storage

### Database Type
**PostgreSQL 16** (follows pg_mcp pattern)

### Connection Details
- **Host:** PostgreSQL container (see docker-compose.yml)
- **Port:** 5432 (internal), 5436 (external for development)
- **Database:** postgres (main database)
- **Schema:** `mcp_smoke` (dedicated schema for this MCP)
- **User:** `mcp`
- **Password:** `mcp`
- **Connection Pattern:** asyncpg with connection pooling

### Purpose
- Track active test sessions
- Store test history with metadata
- Cache comparison results for reporting
- Store preset usage statistics
- Store HTML report metadata and file paths

### Schema Requirements

**Schema Name:** `mcp_smoke`

#### Schema Creation (postgres-init/015_mcp_smoke_schema.sql)
```sql
-- Create dedicated schema
CREATE SCHEMA IF NOT EXISTS mcp_smoke;

-- Grant permissions to mcp user
GRANT ALL PRIVILEGES ON SCHEMA mcp_smoke TO mcp;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mcp_smoke TO mcp;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA mcp_smoke TO mcp;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_smoke GRANT ALL ON TABLES TO mcp;
ALTER DEFAULT PRIVILEGES IN SCHEMA mcp_smoke GRANT ALL ON SEQUENCES TO mcp;

-- Set search path for mcp user
ALTER USER mcp SET search_path TO mcp_smoke, public;
```

#### Table: mcp_smoke.test_sessions
```sql
CREATE TABLE mcp_smoke.test_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    test_type VARCHAR(50) NOT NULL,
    preset VARCHAR(50) NOT NULL,
    test_folder TEXT NOT NULL,
    status VARCHAR(20) NOT NULL, -- active, completed, failed, archived
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    notes TEXT,
    CONSTRAINT test_sessions_status_check CHECK (status IN ('active', 'completed', 'failed', 'archived'))
);

CREATE INDEX idx_test_sessions_status ON mcp_smoke.test_sessions(status);
CREATE INDEX idx_test_sessions_created ON mcp_smoke.test_sessions(created_at DESC);
```

#### Table: mcp_smoke.test_files
```sql
CREATE TABLE mcp_smoke.test_files (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    file_role VARCHAR(20) NOT NULL, -- source, target
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    row_count INTEGER,
    column_count INTEGER,
    s3_key TEXT NULL,
    downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT test_files_session_fk FOREIGN KEY (session_id) REFERENCES mcp_smoke.test_sessions(session_id) ON DELETE CASCADE,
    CONSTRAINT test_files_role_check CHECK (file_role IN ('source', 'target'))
);

CREATE INDEX idx_test_files_session ON mcp_smoke.test_files(session_id);
```

#### Table: mcp_smoke.comparison_results
```sql
CREATE TABLE mcp_smoke.comparison_results (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    source_file_id INTEGER NOT NULL,
    target_file_id INTEGER NOT NULL,
    match_score NUMERIC(5, 2), -- 0.00 to 100.00
    quality_rating VARCHAR(20), -- Pass, Warning, Fail
    matched_rows INTEGER,
    mismatched_rows INTEGER,
    source_only_rows INTEGER,
    target_only_rows INTEGER,
    comparison_time_seconds NUMERIC(10, 3),
    html_report_path TEXT,
    zip_package_path TEXT,
    summary_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT comparison_results_session_fk FOREIGN KEY (session_id) REFERENCES mcp_smoke.test_sessions(session_id) ON DELETE CASCADE,
    CONSTRAINT comparison_results_source_fk FOREIGN KEY (source_file_id) REFERENCES mcp_smoke.test_files(id) ON DELETE CASCADE,
    CONSTRAINT comparison_results_target_fk FOREIGN KEY (target_file_id) REFERENCES mcp_smoke.test_files(id) ON DELETE CASCADE
);

CREATE INDEX idx_comparison_results_session ON mcp_smoke.comparison_results(session_id);
```

#### Table: mcp_smoke.mismatch_details
```sql
CREATE TABLE mcp_smoke.mismatch_details (
    id SERIAL PRIMARY KEY,
    comparison_id INTEGER NOT NULL,
    row_number INTEGER NOT NULL,
    column_name VARCHAR(200) NOT NULL,
    source_value TEXT,
    target_value TEXT,
    CONSTRAINT mismatch_details_comparison_fk FOREIGN KEY (comparison_id) REFERENCES mcp_smoke.comparison_results(id) ON DELETE CASCADE
);

CREATE INDEX idx_mismatch_details_comparison ON mcp_smoke.mismatch_details(comparison_id);
CREATE INDEX idx_mismatch_details_column ON mcp_smoke.mismatch_details(column_name);
```

### Connection Pooling
- **Driver:** asyncpg (async PostgreSQL driver)
- **Pool Size:** 10 connections minimum, 20 maximum
- **Connection Timeout:** 30 seconds
- **Command Timeout:** 60 seconds
- **Pool Configuration:**
  ```python
  pool = await asyncpg.create_pool(
      host=os.getenv('POSTGRES_HOST', 'localhost'),
      port=int(os.getenv('POSTGRES_PORT', '5436')),
      database=os.getenv('POSTGRES_DB', 'postgres'),
      user=os.getenv('POSTGRES_USER', 'mcp'),
      password=os.getenv('POSTGRES_PASSWORD', 'mcp'),
      min_size=10,
      max_size=20,
      command_timeout=60,
      server_settings={'search_path': 'mcp_smoke, public'}
  )
  ```

### Migration Strategy
- Use postgres-init for initial schema creation
- Create `015_mcp_smoke_schema.sql` in pg_mcp/postgres-init/
- Schema will be created automatically when PostgreSQL container starts
- For updates, use versioned migration files: `016_mcp_smoke_update_*.sql`

---

## 8. Configuration Structure

### Environment Variables Required

```bash
# StorageGrid Presets
STORAGEGRID_PROD_ACCESS_KEY=""
STORAGEGRID_PROD_SECRET_KEY=""
STORAGEGRID_STAGING_ACCESS_KEY=""
STORAGEGRID_STAGING_SECRET_KEY=""

# Oracle Presets
ORACLE_PROD_HOST=""
ORACLE_PROD_SERVICE=""
ORACLE_PROD_USER=""
ORACLE_PROD_PASSWORD=""
ORACLE_STAGING_HOST=""
ORACLE_STAGING_SERVICE=""
ORACLE_STAGING_USER=""
ORACLE_STAGING_PASSWORD=""

# MySQL Presets
MYSQL_PROD_HOST=""
MYSQL_PROD_DB=""
MYSQL_PROD_USER=""
MYSQL_PROD_PASSWORD=""
MYSQL_STAGING_HOST=""
MYSQL_STAGING_DB=""
MYSQL_STAGING_USER=""
MYSQL_STAGING_PASSWORD=""

# PostgreSQL Database (for session tracking)
POSTGRES_HOST=localhost
POSTGRES_PORT=5436
POSTGRES_DB=postgres
POSTGRES_USER=mcp
POSTGRES_PASSWORD=mcp
POSTGRES_SCHEMA=mcp_smoke

# Authentication (API Key-Based)
AUTH_ENABLED=true  # Set to false to disable authentication
ADMIN_API_KEY="admin-key-replace-with-secure-random"  # Admin role - full access
DBA_API_KEY="dba-key-replace-with-secure-random"      # DBA role - database exports only
USER_API_KEY="user-key-replace-with-secure-random"    # User role - standard smoke tests
# Generate secure keys: python -c "import secrets; print(secrets.token_urlsafe(32))"

# GitHub Feedback System
GITHUB_TOKEN=""
GITHUB_REPO="your-org/mcp_smoke"

# MCP Configuration
MCP_PORT=8200
MCP_HOST=0.0.0.0
MCP_LOG_LEVEL=INFO

# Test Configuration
DEFAULT_TEST_FOLDER=./tests
DEFAULT_ARCHIVE_FOLDER=./tests/archive
DEFAULT_UPLOAD_FOLDER=./uploads
MAX_CONCURRENT_SESSIONS=10
CSV_CHUNK_SIZE=10000
STREAMING_THRESHOLD_MB=100
MAX_UPLOAD_SIZE_MB=5120  # 5GB limit for uploaded files

# HTML Report Configuration
MAX_MISMATCHES_IN_REPORT=5000
REPORT_ROWS_PER_PAGE=100
GENERATE_ZIP_REPORTS=true
REPORT_INCLUDE_CHARTS=true
REPORT_FORMATS=html  # Options: html, csv, both
```

### settings.yaml Structure

```yaml
mcp:
  name: "mcp_smoke"
  version: "1.0.0"
  description: "Smoke Test Automation MCP"

server:
  host: "${MCP_HOST}"
  port: "${MCP_PORT}"
  log_level: "${MCP_LOG_LEVEL}"
  
  # ========================================
  # AUTHENTICATION (API Key-Based)
  # ========================================
  # Clients must provide API key in Authorization header
  # Format: Authorization: Bearer <api_key>
  authentication:
    enabled: "${AUTH_ENABLED}"  # Set to true to enable
    api_keys:
      - name: "admin"
        key: "${ADMIN_API_KEY}"
        role: "admin"
        description: "Administrator - full access to all tools"
      
      - name: "dba"
        key: "${DBA_API_KEY}"
        role: "dba"
        description: "DBA - database export tools only"
      
      - name: "user"
        key: "${USER_API_KEY}"
        role: "user"
        description: "Standard user - smoke test tools"
      
      - name: "development"
        key: "dev-api-key-12345"
        role: "user"
        description: "Development and testing (insecure key)"
    
    # Public endpoints (no authentication required)
    public_endpoints:
      - "/health"
      - "/healthz"
      - "/health/deep"
      - "/version"
      - "/_info"
  
  # Session tracking
  session:
    extract_from_headers: ["x-session-id", "x-connection-id"]
    fallback_to_fingerprint: true  # Use IP + User-Agent if no header

storagegrid:
  presets:
    # (See section 3 for full preset definitions)

oracle:
  presets:
    # (See section 3 for full preset definitions)

mysql:
  presets:
    # (See section 3 for full preset definitions)

smoke_test:
  test_folder: "${DEFAULT_TEST_FOLDER}"
  archive_folder: "${DEFAULT_ARCHIVE_FOLDER}"
  upload_folder: "${DEFAULT_UPLOAD_FOLDER}"
  max_concurrent_sessions: "${MAX_CONCURRENT_SESSIONS}"
  max_upload_size_mb: "${MAX_UPLOAD_SIZE_MB}"
  
  file_upload:
    enabled: true
    allowed_extensions: [".csv", ".zip"]
    auto_extract_zip: true
    temp_retention_hours: 24  # Auto-cleanup uploaded files after 24h
    validate_csv_on_upload: true
  
  csv_comparison:
    chunk_size: "${CSV_CHUNK_SIZE}"
    streaming_threshold_mb: "${STREAMING_THRESHOLD_MB}"
    case_sensitive: true
    trim_whitespace: true
    report_live: true
  
  html_report:
    enabled: true
    formats: ["html"]  # Options: "html", "csv", "both"
    max_rows_in_report: "${MAX_MISMATCHES_IN_REPORT}"  # Limit rows in HTML/CSV report
    rows_per_page: "${REPORT_ROWS_PER_PAGE}"  # Pagination in HTML detailed section
    include_charts: "${REPORT_INCLUDE_CHARTS}"  # Include visual charts in HTML summary
    generate_zip: "${GENERATE_ZIP_REPORTS}"  # Package reports as zip
    match_score_thresholds:
      excellent: 99.0  # ≥99% = Green "Excellent"
      good: 95.0       # ≥95% = Yellow "Good"
      warning: 80.0    # ≥80% = Orange "Warning"
                       # <80% = Red "Critical"
    csv_report:
      include_header: true
      delimiter: ","
      include_row_numbers: true
      columns: ["row_number", "column_name", "source_value", "target_value", "difference_type"]
    html_template: "report_template.html"  # Jinja2 template file
  
  document_types:
    statement:
      prefix: "statement"
      required_fields: [contract_number, payment_date, transform_subtype]
      key_format: "{prefix}.{contract_number}.{payment_date}.{transform_subtype}.{extension}"
    
    invoice:
      prefix: "invoice"
      required_fields: [contract_number, partner_contract, currency, payment_date, transform_subtype]
      key_format: "{prefix}.{contract_number}.{partner_contract}.{currency}.{payment_date}.{transform_subtype}.{extension}"
    
    gl:
      prefix: "gl"
      required_fields: [gl_document_type, financial_institution, gl_posting_date]
      key_format: "{gl_document_type}.{financial_institution}.{gl_posting_date}.{extension}"

database:
  type: "postgresql"
  host: "${POSTGRES_HOST}"
  port: "${POSTGRES_PORT}"
  database: "${POSTGRES_DB}"
  user: "${POSTGRES_USER}"
  password: "${POSTGRES_PASSWORD}"
  schema: "${POSTGRES_SCHEMA}"
  pool:
    min_size: 10
    max_size: 20
    command_timeout: 60
    connection_timeout: 30
```

---

## 9. Security Requirements

### Authentication & Authorization

#### API Key-Based Authentication (Based on mcp_db_performance Implementation)

**Authentication Flow:**
1. Client sends request with header: `Authorization: Bearer <api_key>`
2. AuthMiddleware intercepts request
3. Validates API key against configured keys in settings.yaml
4. Extracts role from API key configuration
5. Stores client_id, session_id, role in request.state
6. Allows or denies access

**Public Endpoints (No Auth Required):**
- `/health`, `/healthz`, `/health/deep` - Health checks
- `/version` - Version information
- `/_info` - Server information

**Protected Endpoints (Auth Required):**
- All MCP tools
- File upload endpoints
- Report download endpoints

#### Role-Based Access Control (RBAC)

**Roles:**

**1. Admin Role**
- **Access:** ALL tools and features
- **Purpose:** System administrators, full control
- **API Key:** `ADMIN_API_KEY` from environment
- **Permissions:**
  - All smoke test tools
  - All database export tools
  - User management (future)
  - System configuration (future)

**2. DBA Role**
- **Access:** Database export tools ONLY
- **Purpose:** Database administrators who need to export tables for comparison
- **API Key:** `DBA_API_KEY` from environment
- **Permissions:**
  - `export_database_table` (Oracle/MySQL)
  - `list_presets` (view database presets)
  - `validate_connections` (test database connections)
- **Restrictions:**
  - Cannot access StorageGrid download tools
  - Cannot start smoke tests with StorageGrid
  - Cannot access file upload tools

**3. User Role (Standard)**
- **Access:** Standard smoke test tools
- **Purpose:** Regular users performing smoke tests
- **API Key:** `USER_API_KEY` from environment
- **Permissions:**
  - All smoke test workflows (statement, invoice, GL)
  - File upload and comparison
  - StorageGrid download
  - Report generation
  - Archive management
- **Restrictions:**
  - Cannot export database tables directly (use pre-approved queries only)

#### Implementation Pattern (Decorator-Based)

**Tool Authorization Decorator:**
```python
from tools.tool_auth import require_roles

# Example 1: DBA-only tool
@mcp.tool(
    name="export_database_table",
    description="Export database table to CSV. **Requires admin or dba role.**"
)
@require_roles(['admin', 'dba'])
def export_database_table(session_id: str, db_type: str, table_name: str):
    # Tool implementation
    pass

# Example 2: User-accessible tool (no decorator needed)
@mcp.tool(
    name="compare_csv_files",
    description="Compare CSV files"
)
def compare_csv_files(session_id: str, ignore_columns: List[str] = None):
    # All authenticated users can access
    pass

# Example 3: Admin-only tool
@mcp.tool(
    name="purge_old_sessions",
    description="Delete sessions older than N days. **Requires admin role.**"
)
@require_roles(['admin'])
def purge_old_sessions(days: int = 30):
    # Admin-only cleanup
    pass
```

**Access Denied Response:**
```json
{
  "error": "insufficient_permissions",
  "message": "This tool requires one of these roles: admin, dba",
  "your_role": "user",
  "required_roles": ["admin", "dba"],
  "tool_name": "export_database_table",
  "hint": "Contact your administrator for role assignment"
}
```

#### Session Tracking

**Session ID Extraction (Priority Order):**
1. `X-Session-Id` header (explicit session from client)
2. `X-Connection-Id` header (MCP connection ID)
3. Client fingerprint (SHA256 of IP + User-Agent)
4. Generated UUID (fallback)

**Purpose:**
- Track user activity across multiple tool calls
- Associate all operations with specific user session
- Enable audit logging
- Support resuming interrupted tests

**Database Storage:**
```sql
CREATE TABLE mcp_smoke.api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA256 hash of API key
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0
);

CREATE INDEX idx_api_keys_hash ON mcp_smoke.api_keys(key_hash);
CREATE INDEX idx_api_keys_role ON mcp_smoke.api_keys(role);
```

#### File Structure for Authentication

**server/auth_middleware.py** (copied from mcp_db_performance)
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config):
        super().__init__(app)
        self.config = config
        self.public_path_prefixes = ("/health", "/version", "/_info")
    
    async def dispatch(self, request, call_next):
        # Skip auth for public endpoints
        if request.url.path.startswith(self.public_path_prefixes):
            return await call_next(request)
        
        # Check Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication required",
                        "message": "Use: Authorization: Bearer <api_key>"}
            )
        
        api_key = auth_header[7:]  # Remove "Bearer "
        
        # Validate API key
        key_info = self.config.api_keys.get(api_key)
        if not key_info:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid API key"}
            )
        
        # Extract session ID
        session_id = self._extract_session_id(request)
        
        # Store in request.state
        request.state.client_name = key_info["name"]
        request.state.client_role = key_info["role"]
        request.state.session_id = session_id
        
        return await call_next(request)
```

**server/tools/tool_auth.py** (copied from mcp_db_performance)
```python
from functools import wraps
from typing import List

def require_roles(allowed_roles: List[str]):
    """
    Decorator to restrict tool access by role.
    
    Usage:
        @mcp.tool(name="export_db", description="...")
        @require_roles(['admin', 'dba'])
        def export_db(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get current user's role from context
            user_role = get_current_user_role()
            
            # Admin always has access
            if user_role == "admin":
                return func(*args, **kwargs)
            
            # Check if role is allowed
            if user_role not in [r.lower() for r in allowed_roles]:
                return {
                    "error": "insufficient_permissions",
                    "message": f"Requires roles: {', '.join(allowed_roles)}",
                    "your_role": user_role
                }
            
            # Access granted
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_current_user_role() -> str:
    """Get current user's role from request context"""
    try:
        from tools.feedback_context import get_tracking_info
        tracking = get_tracking_info()
        return tracking.get("client_role", "anonymous").lower()
    except:
        return "anonymous"
```

#### Authentication Data Sensitivity
- **StorageGrid:** Access keys stored in environment variables only
- **Databases:** Credentials in environment variables only
- **MCP Access:** No public exposure, localhost only by default

#### Data Sensitivity
- **API Keys:** NEVER log or return in responses, store as SHA256 hash in database
- **StorageGrid Credentials:** Access keys stored in environment variables only, mask in logs (show first 4 chars only)
- **Database Credentials:** In environment variables only, never in code or logs
- **Downloaded CSV Files:** May contain PII/financial data, store in test folders with restricted permissions (owner read/write only)
- **Session Data:** Associate with hashed API key, not raw key
- **Audit Logs:** Log client_name and role, not API key value

### File Access
- Restrict file operations to test folder and archive folder only
- Validate all file paths to prevent directory traversal
- Limit file size uploads (10GB max)

### Secrets Management
- Never return credentials in tool responses
- Mask AWS keys in logs (show first 4 chars only)
- Use SSL/TLS for all external connections

---

## 10. Performance Requirements

### Large File Support
- Must handle CSV files up to 2GB+
- Streaming mode for files > 100MB
- Memory usage < 500MB for 1GB file comparison
- Chunk size configurable (default 10,000 rows)

### Comparison Speed
- 100MB file comparison: < 60 seconds
- 1GB file comparison: < 10 minutes
- 2GB file comparison: < 30 minutes

### Concurrent Sessions
- Support up to 10 concurrent test sessions
- Each session isolated (separate folder, separate database records)

### Database Performance
- SQLite with WAL mode enabled
- Index on session_id, test_type, status, created_at
- Auto-vacuum enabled

---

## 11. Error Handling & User Experience

### Conversational Flow
- LLM should use natural language, not technical jargon
- Examples:
  - ❌ "session_id stmt_20260204_143015 created"
  - ✅ "I've started a statement test in development. Let's download the source file."

### Progress Updates
- For long operations (large downloads, comparisons), provide progress updates
- Example: "Downloading... 45% complete (5.2 MB / 11.5 MB)"
- Example: "Comparing... processed 250,000 rows, found 3 mismatches so far"

### Error Messages (User-Friendly)
- ❌ "boto3.exceptions.NoSuchKey"
- ✅ "File not found in StorageGrid. Expected key: statement.12345.2026-02-04.CREDORAX.CSV. Check your contract number and date."

### Mismatch Reporting
- Summarize mismatches clearly
- Example: "Found 15 differences: 10 in 'amount' column, 5 in 'status' column"
- Always generate detailed diff file for deep investigation

---

## 12. Testing Strategy

### Unit Tests Required
- StorageGrid key generation (all document types)
- CSV comparison logic (exact match, column filtering, sorting)
- Database export queries
- Zip extraction
- File validation

### Integration Tests Required
- End-to-end statement smoke test (with mock StorageGrid)
- Database table comparison (with test databases)
- Large file handling (generate 1GB test file)

### Mock Data
- Create sample CSV files for testing (small, medium, large)
- Mock StorageGrid responses
- Test database with sample tables

---

## 13. Deployment Considerations

### Docker Compose
- **PostgreSQL Container:** Include postgres:16-alpine with dedicated schema creation
- **Volume Mounts:**
  - Test data volume mount (`./tests:/app/tests`)
  - Archive volume mount (`./tests/archive:/app/archive`)
  - Upload directory (`./uploads:/app/uploads`) - For user-uploaded files
  - PostgreSQL init scripts (`./postgres-init:/docker-entrypoint-initdb.d:ro`)
  - PostgreSQL data persistence (`pg_data:/var/lib/postgresql/data`)
- **Network Configuration:**
  - Internal network for MCP ↔ PostgreSQL communication
  - External port 5436 for PostgreSQL (development only)
  - No external exposure for MCP by default (localhost only)
- **Health Checks:**
  - PostgreSQL: `pg_isready -U mcp -d postgres`
  - MCP Server: HTTP health check on `/healthz`
- **Dependencies:** MCP container waits for PostgreSQL to be healthy
- **Package Installation:** Use `uv` for faster builds
- **Example docker-compose.yml structure:**
  ```yaml
  services:
    postgres:
      image: postgres:16-alpine
      ports:
        - "5436:5432"
      environment:
        POSTGRES_USER: mcp
        POSTGRES_PASSWORD: mcp
        POSTGRES_DB: postgres
      volumes:
        - pg_data:/var/lib/postgresql/data
        - ./postgres-init:/docker-entrypoint-initdb.d:ro
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U mcp -d postgres"]
        interval: 5s
        timeout: 3s
        retries: 20
    
    mcp_smoke:
      build: .
      ports:
        - "8200:8200"
      depends_on:
        postgres:
          condition: service_healthy
      environment:
        POSTGRES_HOST: postgres
        POSTGRES_PORT: 5432
        POSTGRES_USER: mcp
        POSTGRES_PASSWORD: mcp
        POSTGRES_DB: postgres
        POSTGRES_SCHEMA: mcp_smoke
      volumes:
        - ./tests:/app/tests
        - ./tests/archive:/app/archive
  
  volumes:
    pg_data:
  ```

**Example Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies with uv (much faster than pip)
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY server/ ./server/
COPY settings.yaml .

# Create directories
RUN mkdir -p /app/tests /app/uploads /app/archive

# Expose port
EXPOSE 8200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8200/healthz || exit 1

# Run server
CMD ["python", "server/server.py"]
```

### Dependencies

**Package Manager:** `uv` (fast Python package installer)

**Installation:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or on Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install dependencies
uv pip install -r requirements.txt
```

**requirements.txt:**
```txt
fastmcp>=2.0.0
boto3>=1.34.0
oracledb>=2.0.0
aiomysql>=0.2.0
pandas>=2.0.0  # For CSV operations
asyncpg>=0.29.0  # PostgreSQL driver
httpx>=0.27.0  # For GitHub API (feedback system)
starlette>=0.35.0
uvicorn>=0.27.0
python-dotenv>=1.0.0
pyyaml>=6.0.0
jinja2>=3.1.0  # For HTML report templating
python-multipart>=0.0.6  # For file upload handling
aiofiles>=23.2.0  # For async file operations
```

**Development Dependencies (requirements-dev.txt):**
```txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.0.0
ruff>=0.1.0
mypy>=1.5.0
```

**Why uv?**
- 10-100x faster than pip
- Better dependency resolution
- Built-in virtual environment management
- Compatible with pip requirements.txt

### File Structure
```
mcp_smoke/
├── server/
│   ├── server.py
│   ├── mcp_app.py
│   ├── config.py
│   ├── auth_middleware.py          # API key authentication (NEW)
│   ├── db/
│   │   ├── connector.py  # PostgreSQL connection pooling
│   │   └── models.py     # Database models and queries
│   ├── tools/
│   │   ├── tool_auth.py             # Role-based access decorator (NEW)
│   │   ├── feedback_context.py       # Request context tracking (NEW)
│   │   ├── mcp_feedback.py         # GitHub feedback system (standard)
│   │   ├── help_tools.py            # Knowledge base access (standard)
│   │   ├── smoke_test_tools.py      # Main smoke test orchestration
│   │   ├── storagegrid_tools.py     # StorageGrid download tools
│   │   ├── database_tools.py        # Oracle/MySQL export (RESTRICTED: admin/dba only)
│   │   ├── csv_comparison_tools.py  # CSV comparison engine
│   │   ├── file_tools.py            # Zip extraction, preview
│   │   └── file_upload_tools.py     # Handle user-uploaded files
│   ├── services/
│   │   ├── storagegrid_service.py   # StorageGrid client wrapper
│   │   ├── csv_comparer.py          # CSV comparison logic
│   │   ├── html_report_generator.py # HTML report generation
│   │   ├── session_manager.py       # Session tracking and database
│   │   ├── database_exporter.py     # Database export logic
│   │   └── file_handler.py          # File upload/validation handler (NEW)
│   ├── templates/
│   │   └── report_template.html     # HTML report template
│   ├── prompts/
│   │   ├── statement_test_prompt.py
│   │   ├── invoice_test_prompt.py
│   │   └── database_test_prompt.py
│   └── knowledge_base/
│       ├── overview.md
│       ├── workflows.md
│       ├── architecture.md
│       └── troubleshooting.md
├── tests/    # Test folder (created at runtime)
├── uploads/  # User-uploaded files (NEW)
├── .env.example
├── settings.yaml
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml  # Includes PostgreSQL container
└── MCP_REQUIREMENTS.md (this file)
```

---

## 14. Success Criteria

The MCP is complete when:

- ✅ User can say "start statement smoke test" and LLM guides them through the entire workflow
- ✅ All three document types (statement, invoice, GL) work correctly
- ✅ Database table export works for Oracle and MySQL
- ✅ CSV comparison handles 2GB+ files without running out of memory
- ✅ **User can upload files directly to chat (CSV/ZIP) and compare them**
- ✅ **ZIP files are automatically extracted and CSV contents detected**
- ✅ Mismatch reporting is clear and actionable
- ✅ Test sessions are tracked in database
- ✅ **API key authentication works (based on mcp_db_performance implementation)**
- ✅ **Role-based access control restricts DBA tools to admin/dba roles**
- ✅ **Session tracking captures client_id and session_id for audit logging**
- ✅ Configuration presets work for production/staging/development
- ✅ Docker Compose setup works out of the box
- ✅ Knowledge base documentation is comprehensive
- ✅ Error messages are user-friendly, not technical
- ✅ **Package installation uses `uv` for fast builds**

---

## 15. Future Enhancements (Out of Scope for v1.0)

- Excel file comparison support
- JSON file comparison
- REST API smoke testing
- Performance metrics dashboard
- Email/Slack notifications for test completion
- Parallel comparison of multiple file pairs
- AI-powered mismatch analysis (suggest root causes)
- Integration with CI/CD pipelines
- Web UI for test history visualization

---

## Notes for LLM Implementation

### Critical Patterns to Follow

1. **Rule #0 Compliance:** ALL tools must use explicit decorator pattern:
   ```python
   @mcp.tool(name="tool_name", description="...")
   def tool_name(...):  # No async, no return type
   ```

2. **Session Management:** Use SQLite to track sessions, never rely on in-memory state

3. **File Safety:** Always validate paths, use absolute paths, check existence before operations

4. **CSV Handling:** Use pandas for small files, csv module with chunking for large files

5. **StorageGrid Integration:** Copy the provided StorageGrid class, adapt as needed

6. **Interactive Flow:** Design tool responses to facilitate natural conversation with LLM

7. **Progress Reporting:** For operations > 5 seconds, return progress updates

8. **Error Context:** Always include enough context in errors for user to fix issue

### Implementation Priority

**Phase 1 (MVP):**
- start_smoke_test (statement only)
- download_storagegrid_file
- compare_csv_files (basic)
- Session tracking database

**Phase 2:**
- Invoice and GL support
- extract_zip_file
- preview_csv_file
- Advanced comparison options

**Phase 3:**
- Database export tools
- Prompts for guided workflows
- Archive functionality
- Validation tools

---

**END OF REQUIREMENTS**

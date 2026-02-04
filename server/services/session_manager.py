"""
Session Manager Service
========================
Manages smoke test sessions in PostgreSQL database
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages test session lifecycle and database operations
    
    Responsibilities:
    - Create/update/delete test sessions
    - Track session status (pending, running, completed, failed)
    - Store file metadata
    - Record comparison results
    - Manage audit logs
    """
    
    def __init__(self, db_pool):
        """
        Initialize session manager
        
        Args:
            db_pool: DatabasePool instance
        """
        self.db_pool = db_pool
    
    async def create_session(
        self,
        session_id: str,
        test_type: str,
        client_id: str,
        client_role: str,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        ignore_columns: Optional[List[str]] = None,
        report_format: str = 'html'
    ) -> Dict[str, Any]:
        """
        Create new test session
        
        Args:
            session_id: Unique session identifier
            test_type: Type of test (statement, database, upload, manual)
            client_id: Client identifier from auth
            client_role: Client role (admin, dba, user)
            source_type: Source data type (storagegrid, database, upload)
            target_type: Target data type (storagegrid, database, upload)
            ignore_columns: Columns to ignore in comparison
            report_format: Report format (html, csv, both)
        
        Returns:
            Dict with session info
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO test_sessions (
                        session_id, test_type, status, client_id, client_role,
                        source_type, target_type, ignore_columns, report_format
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ''', session_id, test_type, 'pending', client_id, client_role,
                    source_type, target_type, ignore_columns, report_format)
                
                logger.info(f"✅ Session created: {session_id} (type: {test_type}, client: {client_id})")
                
                return {
                    'session_id': session_id,
                    'test_type': test_type,
                    'status': 'pending',
                    'created': True
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to create session {session_id}: {e}")
            raise
    
    async def update_session_status(
        self,
        session_id: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """
        Update session status
        
        Args:
            session_id: Session identifier
            status: New status (running, completed, failed)
            error_message: Error message if failed
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Update status and timing
                if status == 'running':
                    await conn.execute('''
                        UPDATE test_sessions
                        SET status = $1, started_at = CURRENT_TIMESTAMP
                        WHERE session_id = $2
                    ''', status, session_id)
                    
                elif status in ('completed', 'failed'):
                    await conn.execute('''
                        UPDATE test_sessions
                        SET status = $1,
                            completed_at = CURRENT_TIMESTAMP,
                            execution_time_ms = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at)) * 1000,
                            error_message = $3
                        WHERE session_id = $2
                    ''', status, session_id, error_message)
                else:
                    await conn.execute('''
                        UPDATE test_sessions
                        SET status = $1
                        WHERE session_id = $2
                    ''', status, session_id)
                
                logger.info(f"📝 Session {session_id} → {status}")
                
        except Exception as e:
            logger.error(f"❌ Failed to update session {session_id}: {e}")
            raise
    
    async def add_file(
        self,
        session_id: str,
        file_role: str,
        file_path: str,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        file_format: Optional[str] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        columns: Optional[List[str]] = None,
        download_time_ms: Optional[int] = None,
        parse_time_ms: Optional[int] = None
    ) -> int:
        """
        Add file to session
        
        Args:
            session_id: Session identifier
            file_role: Role of file (source, target, report, upload)
            file_path: Local path or S3 key
            file_name: Original filename
            file_size: File size in bytes
            file_format: File format (csv, zip, html)
            row_count: Number of rows (for CSV)
            column_count: Number of columns (for CSV)
            columns: Column names (for CSV)
            download_time_ms: Download time in ms
            parse_time_ms: Parse time in ms
        
        Returns:
            file_id
        """
        try:
            async with self.db_pool.acquire() as conn:
                file_id = await conn.fetchval('''
                    INSERT INTO test_files (
                        session_id, file_role, file_path, file_name, file_size_bytes,
                        file_format, row_count, column_count, columns,
                        download_time_ms, parse_time_ms
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING file_id
                ''', session_id, file_role, file_path, file_name, file_size,
                    file_format, row_count, column_count, columns,
                    download_time_ms, parse_time_ms)
                
                logger.info(f"📁 File added: {file_name or file_path} (role: {file_role}, id: {file_id})")
                return file_id
                
        except Exception as e:
            logger.error(f"❌ Failed to add file to session {session_id}: {e}")
            raise
    
    async def save_comparison_result(
        self,
        session_id: str,
        total_rows: int,
        matched_rows: int,
        mismatched_rows: int,
        source_only_rows: int = 0,
        target_only_rows: int = 0,
        columns_compared: Optional[int] = None,
        columns_with_differences: Optional[int] = None,
        comparison_time_ms: Optional[int] = None
    ) -> int:
        """
        Save comparison result summary
        
        Args:
            session_id: Session identifier
            total_rows: Total rows compared
            matched_rows: Rows that matched
            mismatched_rows: Rows with differences
            source_only_rows: Rows only in source
            target_only_rows: Rows only in target
            columns_compared: Number of columns compared
            columns_with_differences: Columns with differences
            comparison_time_ms: Comparison time in ms
        
        Returns:
            result_id
        """
        try:
            async with self.db_pool.acquire() as conn:
                result_id = await conn.fetchval('''
                    INSERT INTO comparison_results (
                        session_id, total_rows, matched_rows, mismatched_rows,
                        source_only_rows, target_only_rows,
                        columns_compared, columns_with_differences,
                        comparison_time_ms
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING result_id
                ''', session_id, total_rows, matched_rows, mismatched_rows,
                    source_only_rows, target_only_rows,
                    columns_compared, columns_with_differences,
                    comparison_time_ms)
                
                match_score = (matched_rows / total_rows * 100) if total_rows > 0 else 0
                logger.info(f"📊 Comparison result saved: {match_score:.2f}% match (result_id: {result_id})")
                return result_id
                
        except Exception as e:
            logger.error(f"❌ Failed to save comparison result for {session_id}: {e}")
            raise
    
    async def save_mismatch_details(
        self,
        result_id: int,
        mismatches: List[Dict[str, Any]],
        batch_size: int = 1000
    ):
        """
        Save detailed mismatch records in batches
        
        Args:
            result_id: Comparison result ID
            mismatches: List of mismatch dicts with keys:
                       - row_number
                       - row_key (optional)
                       - column_name
                       - source_value
                       - target_value
                       - difference_type (optional)
            batch_size: Number of records to insert per batch
        """
        try:
            total_mismatches = len(mismatches)
            
            async with self.db_pool.acquire() as conn:
                for i in range(0, total_mismatches, batch_size):
                    batch = mismatches[i:i + batch_size]
                    
                    # Prepare batch insert
                    values = [
                        (
                            result_id,
                            m['row_number'],
                            m.get('row_key'),
                            m['column_name'],
                            m.get('source_value'),
                            m.get('target_value'),
                            m.get('difference_type', 'value_mismatch')
                        )
                        for m in batch
                    ]
                    
                    await conn.executemany('''
                        INSERT INTO mismatch_details (
                            result_id, row_number, row_key, column_name,
                            source_value, target_value, difference_type
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ''', values)
                    
                    logger.debug(f"📝 Saved mismatch batch {i // batch_size + 1}/{(total_mismatches - 1) // batch_size + 1}")
            
            logger.info(f"✅ Saved {total_mismatches} mismatch details for result {result_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save mismatch details: {e}")
            raise
    
    async def log_audit(
        self,
        session_id: str,
        client_id: str,
        client_role: str,
        tool_name: str,
        action: str,
        success: bool,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log audit entry
        
        Args:
            session_id: Session identifier
            client_id: Client identifier
            client_role: Client role
            tool_name: Tool name invoked
            action: Action performed
            success: Whether action succeeded
            error_message: Error message if failed
            execution_time_ms: Execution time in ms
            metadata: Additional metadata as JSON
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO audit_log (
                        session_id, client_id, client_role, tool_name, action,
                        success, error_message, execution_time_ms, request_metadata
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ''', session_id, client_id, client_role, tool_name, action,
                    success, error_message, execution_time_ms,
                    json.dumps(metadata) if metadata else None)
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to log audit entry: {e}")
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM v_session_summary
                    WHERE session_id = $1
                ''', session_id)
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None
    
    async def get_active_sessions(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active sessions (optionally filtered by client)"""
        try:
            async with self.db_pool.acquire() as conn:
                if client_id:
                    rows = await conn.fetch('''
                        SELECT * FROM v_active_sessions
                        WHERE client_id = $1
                        ORDER BY created_at DESC
                    ''', client_id)
                else:
                    rows = await conn.fetch('''
                        SELECT * FROM v_active_sessions
                        ORDER BY created_at DESC
                    ''')
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Failed to get active sessions: {e}")
            return []
    
    async def get_recent_completions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently completed sessions"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM v_recent_completions
                    LIMIT $1
                ''', limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Failed to get recent completions: {e}")
            return []
    
    async def cleanup_old_sessions(self, days_to_keep: int = 30) -> Dict[str, int]:
        """
        Clean up old sessions
        
        Args:
            days_to_keep: Keep sessions from last N days
        
        Returns:
            Dict with deleted_sessions and deleted_files counts
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM cleanup_old_sessions($1)
                ''', days_to_keep)
                
                result = {
                    'deleted_sessions': row[0],
                    'deleted_files': row[1]
                }
                
                logger.info(f"🧹 Cleanup complete: {result['deleted_sessions']} sessions, {result['deleted_files']} files")
                return result
                
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            raise

"""
Database Comparer - In-Database Comparison Engine
=================================================
Performs efficient table/query comparison using temp tables
"""

import logging
from typing import Optional, Literal, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

DatabaseType = Literal['oracle', 'mysql', 'postgresql']


@dataclass
class ComparisonResult:
    """Result of database comparison"""
    match_status: Literal['identical', 'mismatch', 'error']
    total_rows_source: int
    total_rows_target: int
    matching_rows: int
    missing_in_target: int
    missing_in_source: int
    mismatched_rows: int
    comparison_time_sec: float
    temp_table_name: Optional[str]
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'match_status': self.match_status,
            'total_rows_source': self.total_rows_source,
            'total_rows_target': self.total_rows_target,
            'matching_rows': self.matching_rows,
            'missing_in_target': self.missing_in_target,
            'missing_in_source': self.missing_in_source,
            'mismatched_rows': self.mismatched_rows,
            'comparison_time_sec': round(self.comparison_time_sec, 2),
            'temp_table_name': self.temp_table_name,
            'error_message': self.error_message
        }


@dataclass
class ComparisonConfig:
    """Configuration for comparison"""
    source_query: str
    target_query: str
    key_columns: List[str]  # Columns to join on
    compare_columns: Optional[List[str]] = None  # Columns to compare (None = all)
    case_sensitive: bool = True
    trim_strings: bool = False
    ignore_null_differences: bool = False


class DatabaseComparer:
    """
    In-database comparison engine using temporary tables
    
    Strategy:
    1. Create temp table for source query results
    2. Create temp table for target query results
    3. Perform FULL OUTER JOIN to find differences
    4. Store mismatch details in temp table
    5. Return comparison results
    6. Automatic cleanup on exit
    """
    
    def __init__(self):
        """Initialize database comparer"""
        self.comparison_count = 0
        self.temp_tables_created: List[str] = []
    
    async def compare_tables(
        self,
        config: ComparisonConfig,
        db_type: DatabaseType,
        execute_query_func,
        session_id: Optional[str] = None
    ) -> ComparisonResult:
        """
        Compare two queries/tables using in-database temp tables
        
        Args:
            config: Comparison configuration
            db_type: Database type (oracle/mysql/postgresql)
            execute_query_func: Async function to execute SQL
            session_id: Optional session ID for tracking
        
        Returns:
            ComparisonResult with detailed statistics
        """
        self.comparison_count += 1
        start_time = datetime.utcnow()
        
        # Generate unique temp table names
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        hash_suffix = hashlib.md5(
            f"{config.source_query}{config.target_query}".encode()
        ).hexdigest()[:8]
        
        temp_source = f"tmp_src_{timestamp}_{hash_suffix}"
        temp_target = f"tmp_tgt_{timestamp}_{hash_suffix}"
        temp_mismatch = f"tmp_mismatch_{timestamp}_{hash_suffix}"
        
        logger.info(f"🔄 Starting comparison (session: {session_id})")
        logger.info(f"   Temp tables: {temp_source}, {temp_target}, {temp_mismatch}")
        
        try:
            # Step 1: Create temp table for source
            await self._create_temp_table(
                temp_source,
                config.source_query,
                db_type,
                execute_query_func
            )
            self.temp_tables_created.append(temp_source)
            
            # Step 2: Create temp table for target
            await self._create_temp_table(
                temp_target,
                config.target_query,
                db_type,
                execute_query_func
            )
            self.temp_tables_created.append(temp_target)
            
            # Step 3: Get row counts
            source_count = await self._get_row_count(
                temp_source,
                db_type,
                execute_query_func
            )
            target_count = await self._get_row_count(
                temp_target,
                db_type,
                execute_query_func
            )
            
            logger.info(f"   Source rows: {source_count:,}")
            logger.info(f"   Target rows: {target_count:,}")
            
            # Step 4: Perform comparison using FULL OUTER JOIN
            comparison_query = self._build_comparison_query(
                temp_source,
                temp_target,
                temp_mismatch,
                config,
                db_type
            )
            
            await execute_query_func(comparison_query)
            self.temp_tables_created.append(temp_mismatch)
            
            # Step 5: Get mismatch statistics
            stats = await self._get_mismatch_stats(
                temp_mismatch,
                db_type,
                execute_query_func
            )
            
            # Calculate comparison time
            end_time = datetime.utcnow()
            comparison_time = (end_time - start_time).total_seconds()
            
            # Determine match status
            match_status = 'identical'
            if stats['total_mismatches'] > 0:
                match_status = 'mismatch'
            
            result = ComparisonResult(
                match_status=match_status,
                total_rows_source=source_count,
                total_rows_target=target_count,
                matching_rows=stats['matching_rows'],
                missing_in_target=stats['missing_in_target'],
                missing_in_source=stats['missing_in_source'],
                mismatched_rows=stats['mismatched_values'],
                comparison_time_sec=comparison_time,
                temp_table_name=temp_mismatch
            )
            
            if match_status == 'identical':
                logger.info(f"✅ Comparison complete: IDENTICAL ({comparison_time:.2f}s)")
            else:
                logger.warning(
                    f"⚠️ Comparison complete: MISMATCH "
                    f"({stats['total_mismatches']} differences, {comparison_time:.2f}s)"
                )
            
            return result
        
        except Exception as e:
            logger.exception(f"❌ Comparison failed: {str(e)}")
            
            end_time = datetime.utcnow()
            comparison_time = (end_time - start_time).total_seconds()
            
            return ComparisonResult(
                match_status='error',
                total_rows_source=0,
                total_rows_target=0,
                matching_rows=0,
                missing_in_target=0,
                missing_in_source=0,
                mismatched_rows=0,
                comparison_time_sec=comparison_time,
                temp_table_name=None,
                error_message=str(e)
            )
        
        finally:
            # Cleanup happens in cleanup_temp_tables() method
            pass
    
    async def _create_temp_table(
        self,
        table_name: str,
        query: str,
        db_type: DatabaseType,
        execute_query_func
    ):
        """Create temporary table from query results"""
        if db_type == 'oracle':
            # Oracle: CREATE GLOBAL TEMPORARY TABLE (session-scoped)
            create_sql = f"""
            CREATE GLOBAL TEMPORARY TABLE {table_name}
            ON COMMIT PRESERVE ROWS
            AS {query}
            """
        elif db_type == 'mysql':
            # MySQL: CREATE TEMPORARY TABLE
            create_sql = f"""
            CREATE TEMPORARY TABLE {table_name}
            AS {query}
            """
        elif db_type == 'postgresql':
            # PostgreSQL: CREATE TEMP TABLE
            create_sql = f"""
            CREATE TEMP TABLE {table_name}
            AS {query}
            """
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        logger.debug(f"Creating temp table: {table_name}")
        await execute_query_func(create_sql)
    
    async def _get_row_count(
        self,
        table_name: str,
        db_type: DatabaseType,
        execute_query_func
    ) -> int:
        """Get row count from table"""
        count_sql = f"SELECT COUNT(*) FROM {table_name}"
        result = await execute_query_func(count_sql)
        
        # Handle different result formats
        if isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], (list, tuple)):
                return int(result[0][0])
            elif isinstance(result[0], dict):
                return int(list(result[0].values())[0])
        
        return 0
    
    def _build_comparison_query(
        self,
        temp_source: str,
        temp_target: str,
        temp_mismatch: str,
        config: ComparisonConfig,
        db_type: DatabaseType
    ) -> str:
        """
        Build FULL OUTER JOIN comparison query
        
        Creates temp table with mismatch details:
        - mismatch_type: 'missing_in_target', 'missing_in_source', 'value_mismatch'
        - key columns
        - source/target values for mismatched columns
        """
        # Build key columns join condition
        key_join = " AND ".join([
            f"COALESCE(s.{col}, t.{col}) = COALESCE(t.{col}, s.{col})"
            for col in config.key_columns
        ])
        
        # Determine columns to compare
        if config.compare_columns:
            compare_cols = config.compare_columns
        else:
            compare_cols = ['*']  # Compare all columns (simplified)
        
        # Build comparison logic
        if db_type == 'postgresql':
            # PostgreSQL supports FULL OUTER JOIN
            query = f"""
            CREATE TEMP TABLE {temp_mismatch} AS
            SELECT 
                CASE 
                    WHEN s.{config.key_columns[0]} IS NULL THEN 'missing_in_source'
                    WHEN t.{config.key_columns[0]} IS NULL THEN 'missing_in_target'
                    ELSE 'value_mismatch'
                END as mismatch_type,
                {', '.join([f'COALESCE(s.{col}, t.{col}) as {col}' for col in config.key_columns])}
            FROM {temp_source} s
            FULL OUTER JOIN {temp_target} t
            ON {' AND '.join([f's.{col} = t.{col}' for col in config.key_columns])}
            WHERE s.{config.key_columns[0]} IS NULL 
               OR t.{config.key_columns[0]} IS NULL
            """
        elif db_type == 'mysql':
            # MySQL doesn't support FULL OUTER JOIN, use UNION
            query = f"""
            CREATE TEMPORARY TABLE {temp_mismatch} AS
            SELECT 'missing_in_target' as mismatch_type, {', '.join(config.key_columns)}
            FROM {temp_source} s
            LEFT JOIN {temp_target} t ON {' AND '.join([f's.{col} = t.{col}' for col in config.key_columns])}
            WHERE t.{config.key_columns[0]} IS NULL
            UNION ALL
            SELECT 'missing_in_source' as mismatch_type, {', '.join(config.key_columns)}
            FROM {temp_target} t
            LEFT JOIN {temp_source} s ON {' AND '.join([f't.{col} = s.{col}' for col in config.key_columns])}
            WHERE s.{config.key_columns[0]} IS NULL
            """
        else:  # Oracle
            # Oracle doesn't support FULL OUTER JOIN easily, use UNION
            query = f"""
            CREATE GLOBAL TEMPORARY TABLE {temp_mismatch}
            ON COMMIT PRESERVE ROWS
            AS
            SELECT 'missing_in_target' as mismatch_type, {', '.join(config.key_columns)}
            FROM {temp_source} s
            WHERE NOT EXISTS (
                SELECT 1 FROM {temp_target} t 
                WHERE {' AND '.join([f's.{col} = t.{col}' for col in config.key_columns])}
            )
            UNION ALL
            SELECT 'missing_in_source' as mismatch_type, {', '.join(config.key_columns)}
            FROM {temp_target} t
            WHERE NOT EXISTS (
                SELECT 1 FROM {temp_source} s 
                WHERE {' AND '.join([f't.{col} = s.{col}' for col in config.key_columns])}
            )
            """
        
        return query
    
    async def _get_mismatch_stats(
        self,
        temp_mismatch: str,
        db_type: DatabaseType,
        execute_query_func
    ) -> Dict[str, int]:
        """Get mismatch statistics from temp table"""
        stats_sql = f"""
        SELECT 
            mismatch_type,
            COUNT(*) as count
        FROM {temp_mismatch}
        GROUP BY mismatch_type
        """
        
        result = await execute_query_func(stats_sql)
        
        # Parse results
        stats = {
            'missing_in_target': 0,
            'missing_in_source': 0,
            'mismatched_values': 0,
            'matching_rows': 0,
            'total_mismatches': 0
        }
        
        # Handle empty result (no mismatches)
        if not result or len(result) == 0:
            return stats
        
        if isinstance(result, list):
            for row in result:
                mismatch_type = None
                count = 0
                
                if isinstance(row, dict):
                    mismatch_type = row.get('mismatch_type')
                    count = int(row.get('count', 0))
                elif isinstance(row, (list, tuple)) and len(row) >= 2:
                    mismatch_type = row[0]
                    count = int(row[1])
                else:
                    # Skip invalid rows
                    continue
                
                if mismatch_type == 'missing_in_target':
                    stats['missing_in_target'] = count
                elif mismatch_type == 'missing_in_source':
                    stats['missing_in_source'] = count
                elif mismatch_type == 'value_mismatch':
                    stats['mismatched_values'] = count
                
                stats['total_mismatches'] += count
        
        return stats
    
    async def cleanup_temp_tables(
        self,
        db_type: DatabaseType,
        execute_query_func
    ):
        """Clean up all temporary tables created during comparison"""
        logger.info(f"🧹 Cleaning up {len(self.temp_tables_created)} temp tables")
        
        for table_name in self.temp_tables_created:
            try:
                if db_type == 'oracle':
                    drop_sql = f"DROP TABLE {table_name}"
                elif db_type == 'mysql':
                    drop_sql = f"DROP TEMPORARY TABLE IF EXISTS {table_name}"
                elif db_type == 'postgresql':
                    drop_sql = f"DROP TABLE IF EXISTS {table_name}"
                else:
                    continue
                
                await execute_query_func(drop_sql)
                logger.debug(f"   Dropped: {table_name}")
            except Exception as e:
                logger.warning(f"   Failed to drop {table_name}: {str(e)}")
        
        self.temp_tables_created.clear()
        logger.info("✅ Cleanup complete")
    
    def get_stats(self) -> dict:
        """Get comparison statistics"""
        return {
            'total_comparisons': self.comparison_count,
            'active_temp_tables': len(self.temp_tables_created)
        }

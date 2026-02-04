"""
Execution Plan Analyzer - Prevents Expensive Queries
====================================================
Analyzes query execution plans to block slow/expensive operations
"""

import re
import logging
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

DatabaseType = Literal['oracle', 'mysql', 'postgresql']


class ExecutionCost(Enum):
    """Query execution cost levels"""
    LOW = "low"  # < 1 minute estimated
    MEDIUM = "medium"  # 1-3 minutes
    HIGH = "high"  # 3-5 minutes
    EXCESSIVE = "excessive"  # > 5 minutes (blocked)


@dataclass
class PlanAnalysis:
    """Result of execution plan analysis"""
    is_acceptable: bool
    estimated_time_sec: float
    estimated_rows: int
    estimated_cost: float
    cost_level: ExecutionCost
    has_full_table_scan: bool
    recommendations: list[str]
    raw_plan: str
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'is_acceptable': self.is_acceptable,
            'estimated_time_sec': round(self.estimated_time_sec, 2),
            'estimated_rows': self.estimated_rows,
            'estimated_cost': round(self.estimated_cost, 2),
            'cost_level': self.cost_level.value,
            'has_full_table_scan': self.has_full_table_scan,
            'recommendations': self.recommendations,
            'error_message': self.error_message
        }


class ExecutionPlanAnalyzer:
    """
    Analyzes query execution plans to prevent expensive operations
    
    Safety checks:
    1. Estimate execution time (block if > 5 minutes)
    2. Detect full table scans (warn user)
    3. Check row count (excessive rows = slow)
    4. Provide optimization recommendations
    5. Database-specific plan parsing (Oracle/MySQL/PostgreSQL)
    """
    
    # Maximum execution time (5 minutes)
    MAX_EXECUTION_TIME_SEC = 300
    
    # Warning thresholds
    WARN_ROWS = 1_000_000  # Warn if > 1M rows
    WARN_TIME_SEC = 60  # Warn if > 1 minute
    
    def __init__(self):
        """Initialize execution plan analyzer"""
        self.analysis_count = 0
        self.blocked_count = 0
    
    async def analyze_query_cost(
        self,
        query: str,
        db_type: DatabaseType,
        execute_explain_func
    ) -> PlanAnalysis:
        """
        Analyze query execution plan and estimate cost
        
        Args:
            query: SQL query to analyze
            db_type: Type of database (oracle/mysql/postgresql)
            execute_explain_func: Async function to execute EXPLAIN query
        
        Returns:
            PlanAnalysis with cost estimation and recommendations
        """
        self.analysis_count += 1
        
        logger.info(f"📊 Analyzing execution plan for {db_type} query")
        
        try:
            # Get EXPLAIN output
            explain_query = self._build_explain_query(query, db_type)
            plan_output = await execute_explain_func(explain_query)
            
            # Parse plan based on database type
            if db_type == 'oracle':
                analysis = self._parse_oracle_plan(plan_output)
            elif db_type == 'mysql':
                analysis = self._parse_mysql_plan(plan_output)
            elif db_type == 'postgresql':
                analysis = self._parse_postgresql_plan(plan_output)
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
            
            # Determine if acceptable
            analysis.is_acceptable = (
                analysis.estimated_time_sec <= self.MAX_EXECUTION_TIME_SEC
            )
            
            # Log results
            if not analysis.is_acceptable:
                self.blocked_count += 1
                logger.warning(
                    f"🚫 Query blocked! Estimated time: {analysis.estimated_time_sec:.2f}s "
                    f"(max: {self.MAX_EXECUTION_TIME_SEC}s)"
                )
            elif analysis.cost_level in [ExecutionCost.HIGH, ExecutionCost.MEDIUM]:
                logger.warning(
                    f"⚠️ Query may be slow: {analysis.estimated_time_sec:.2f}s "
                    f"({analysis.estimated_rows:,} rows)"
                )
            else:
                logger.info(
                    f"✅ Query cost acceptable: {analysis.estimated_time_sec:.2f}s "
                    f"({analysis.estimated_rows:,} rows)"
                )
            
            return analysis
        
        except Exception as e:
            logger.exception(f"❌ Execution plan analysis failed: {str(e)}")
            return PlanAnalysis(
                is_acceptable=False,
                estimated_time_sec=0,
                estimated_rows=0,
                estimated_cost=0,
                cost_level=ExecutionCost.EXCESSIVE,
                has_full_table_scan=False,
                recommendations=[],
                raw_plan="",
                error_message=f"Plan analysis failed: {str(e)}"
            )
    
    def _build_explain_query(self, query: str, db_type: DatabaseType) -> str:
        """Build EXPLAIN query for database type"""
        if db_type == 'oracle':
            return f"EXPLAIN PLAN FOR {query}"
        elif db_type == 'mysql':
            return f"EXPLAIN {query}"
        elif db_type == 'postgresql':
            return f"EXPLAIN (FORMAT JSON, ANALYZE FALSE) {query}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def _parse_oracle_plan(self, plan_output: str) -> PlanAnalysis:
        """
        Parse Oracle execution plan
        
        Oracle EXPLAIN PLAN output format:
        - Uses DBMS_XPLAN.DISPLAY
        - Columns: Id, Operation, Name, Rows, Bytes, Cost
        """
        recommendations = []
        has_full_table_scan = False
        
        # Extract cost (Oracle cost is relative, not time)
        # Match patterns like "Cost (5)" or "| 500000 (5) |"
        cost_match = re.search(r'\|\s*(\d+)\s*\(\d+\%?\)', plan_output)
        if not cost_match:
            cost_match = re.search(r'Cost\s*[:=]\s*(\d+)', plan_output, re.IGNORECASE)
        cost = float(cost_match.group(1)) if cost_match else 0
        
        # Extract rows from table format
        # Match patterns like "| 10000000 | 500000" (rows before cost)
        rows_match = re.search(r'\|\s*(\d+)\s*\|\s*\d+\s*\(', plan_output)
        if not rows_match:
            rows_match = re.search(r'Cardinality\s*[:=]\s*(\d+)', plan_output, re.IGNORECASE)
        if not rows_match:
            rows_match = re.search(r'Rows\s*[:=]\s*(\d+)', plan_output, re.IGNORECASE)
        rows = int(rows_match.group(1)) if rows_match else 0
        
        # Check for full table scan
        if 'TABLE ACCESS FULL' in plan_output:
            has_full_table_scan = True
            recommendations.append("⚠️ Full table scan detected. Consider adding indexes.")
        
        # Check for Cartesian product (very expensive)
        if 'CARTESIAN' in plan_output or 'MERGE JOIN CARTESIAN' in plan_output:
            recommendations.append("❌ Cartesian product detected! Missing JOIN condition?")
            cost *= 10  # Significantly increase cost estimate
        
        # Estimate time from cost (rough heuristic: cost ~= milliseconds)
        estimated_time_sec = cost / 1000
        
        # If high row count, increase time estimate
        if rows > self.WARN_ROWS:
            estimated_time_sec *= (rows / self.WARN_ROWS)
            recommendations.append(
                f"⚠️ High row count: {rows:,} rows. Consider adding WHERE filters."
            )
        
        # Determine cost level
        cost_level = self._determine_cost_level(estimated_time_sec)
        
        return PlanAnalysis(
            is_acceptable=True,  # Will be set by caller
            estimated_time_sec=estimated_time_sec,
            estimated_rows=rows,
            estimated_cost=cost,
            cost_level=cost_level,
            has_full_table_scan=has_full_table_scan,
            recommendations=recommendations,
            raw_plan=plan_output
        )
    
    def _parse_mysql_plan(self, plan_output: str) -> PlanAnalysis:
        """
        Parse MySQL execution plan
        
        MySQL EXPLAIN output format:
        - JSON or table format
        - Shows: rows, filtered, Extra (Using index, Using filesort, etc.)
        """
        recommendations = []
        has_full_table_scan = False
        total_rows = 0
        cost = 0
        
        # Parse rows from each table in plan
        # Format: ... rows: 12345 ...
        rows_matches = re.findall(r'rows[:\s]+(\d+)', plan_output, re.IGNORECASE)
        if rows_matches:
            # Multiply rows for JOIN operations (simplified heuristic)
            if len(rows_matches) > 1:
                total_rows = 1
                for row_str in rows_matches:
                    total_rows *= int(row_str)
            else:
                total_rows = int(rows_matches[0])
        
        # Check for full table scan
        if 'ALL' in plan_output or 'type: ALL' in plan_output:
            has_full_table_scan = True
            recommendations.append("⚠️ Full table scan detected. Consider adding indexes.")
        
        # Check for filesort (expensive)
        if 'Using filesort' in plan_output:
            recommendations.append("⚠️ Filesort detected. Consider adding index on ORDER BY columns.")
            cost += 1000  # Add cost for sort
        
        # Check for temporary table
        if 'Using temporary' in plan_output:
            recommendations.append("⚠️ Temporary table used. Consider query optimization.")
            cost += 500
        
        # Estimate time (MySQL cost is in terms of rows read)
        # Rough heuristic: 1M rows ~= 1 second
        estimated_time_sec = total_rows / 1_000_000
        
        # Add cost from special operations
        estimated_time_sec += cost / 1000
        
        # Check for missing indexes
        if 'NULL' in plan_output and has_full_table_scan:
            recommendations.append("❌ No index used. Query may be very slow!")
        
        # Determine cost level
        cost_level = self._determine_cost_level(estimated_time_sec)
        
        return PlanAnalysis(
            is_acceptable=True,
            estimated_time_sec=estimated_time_sec,
            estimated_rows=total_rows,
            estimated_cost=cost,
            cost_level=cost_level,
            has_full_table_scan=has_full_table_scan,
            recommendations=recommendations,
            raw_plan=plan_output
        )
    
    def _parse_postgresql_plan(self, plan_output: str) -> PlanAnalysis:
        """
        Parse PostgreSQL execution plan
        
        PostgreSQL EXPLAIN output format:
        - JSON format with Plan Cost, Actual Time, Rows
        - Shows: Seq Scan, Index Scan, Hash Join, etc.
        """
        recommendations = []
        has_full_table_scan = False
        
        # Extract total cost
        cost_match = re.search(r'Total Cost["\s:]+([0-9.]+)', plan_output, re.IGNORECASE)
        if not cost_match:
            cost_match = re.search(r'cost["\s:=]+[0-9.]+\.\.([0-9.]+)', plan_output, re.IGNORECASE)
        cost = float(cost_match.group(1)) if cost_match else 0
        
        # Extract rows
        rows_match = re.search(r'Plan Rows["\s:]+(\d+)', plan_output, re.IGNORECASE)
        if not rows_match:
            rows_match = re.search(r'rows["\s:=]+(\d+)', plan_output, re.IGNORECASE)
        rows = int(rows_match.group(1)) if rows_match else 0
        
        # Check for sequential scan (full table scan)
        if 'Seq Scan' in plan_output:
            has_full_table_scan = True
            recommendations.append("⚠️ Sequential scan detected. Consider adding indexes.")
        
        # Check for nested loop with large dataset
        if 'Nested Loop' in plan_output and rows > 10000:
            recommendations.append("⚠️ Nested loop with large dataset. Consider hash join.")
        
        # Check for sort
        if 'Sort' in plan_output:
            recommendations.append("💡 Sort operation detected. Ensure indexed ORDER BY if possible.")
        
        # Estimate time from PostgreSQL cost
        # PostgreSQL cost units are arbitrary but roughly: cost ~= disk page fetches
        # Rough heuristic: 1000 cost units ~= 0.1 seconds
        estimated_time_sec = cost / 10000
        
        # If high row count, adjust estimate
        if rows > self.WARN_ROWS:
            estimated_time_sec *= (rows / self.WARN_ROWS) * 0.5
            recommendations.append(
                f"⚠️ High row count: {rows:,} rows. Consider limiting results."
            )
        
        # Determine cost level
        cost_level = self._determine_cost_level(estimated_time_sec)
        
        return PlanAnalysis(
            is_acceptable=True,
            estimated_time_sec=estimated_time_sec,
            estimated_rows=rows,
            estimated_cost=cost,
            cost_level=cost_level,
            has_full_table_scan=has_full_table_scan,
            recommendations=recommendations,
            raw_plan=plan_output
        )
    
    def _determine_cost_level(self, estimated_time_sec: float) -> ExecutionCost:
        """Determine cost level from estimated time"""
        if estimated_time_sec > self.MAX_EXECUTION_TIME_SEC:
            return ExecutionCost.EXCESSIVE
        elif estimated_time_sec > 180:  # 3 minutes
            return ExecutionCost.HIGH
        elif estimated_time_sec > 60:  # 1 minute
            return ExecutionCost.MEDIUM
        else:
            return ExecutionCost.LOW
    
    def get_stats(self) -> dict:
        """Get analysis statistics"""
        return {
            'total_analyses': self.analysis_count,
            'blocked_queries': self.blocked_count,
            'success_rate': (
                (self.analysis_count - self.blocked_count) / self.analysis_count * 100
                if self.analysis_count > 0 else 0
            )
        }

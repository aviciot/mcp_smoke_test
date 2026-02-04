"""
Database Validator - Checks Database Availability
==================================================
Validates database connections before executing queries
"""

import asyncio
import logging
from typing import Optional, Literal
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

DatabaseType = Literal['oracle', 'mysql', 'postgresql']


@dataclass
class DatabaseInfo:
    """Database connection information"""
    host: str
    port: int
    database: str
    db_type: DatabaseType
    description: Optional[str] = None


@dataclass
class AvailabilityResult:
    """Result of database availability check"""
    is_available: bool
    db_type: DatabaseType
    response_time_ms: float
    version: Optional[str]
    error_message: Optional[str]
    timestamp: datetime
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'is_available': self.is_available,
            'db_type': self.db_type,
            'response_time_ms': round(self.response_time_ms, 2),
            'version': self.version,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat()
        }


class DatabaseValidator:
    """
    Validates database availability and connectivity
    
    Safety checks:
    1. Connection test (can we reach the database?)
    2. Latency check (is response time acceptable?)
    3. Version check (what database version is running?)
    4. Error handling (graceful failure with user-friendly messages)
    """
    
    # Maximum acceptable response time (milliseconds)
    MAX_RESPONSE_TIME_MS = 5000  # 5 seconds
    
    def __init__(self):
        """Initialize database validator"""
        self.check_count = 0
        self.failed_count = 0
    
    async def check_availability(
        self,
        db_info: DatabaseInfo,
        timeout_sec: int = 10
    ) -> AvailabilityResult:
        """
        Check if database is available and responsive
        
        Args:
            db_info: Database connection information
            timeout_sec: Maximum time to wait for response
        
        Returns:
            AvailabilityResult with connection status
        """
        self.check_count += 1
        start_time = asyncio.get_event_loop().time()
        
        logger.info(
            f"🔍 Checking {db_info.db_type} database availability: "
            f"{db_info.host}:{db_info.port}/{db_info.database}"
        )
        
        try:
            # Check based on database type
            if db_info.db_type == 'oracle':
                result = await self._check_oracle(db_info, timeout_sec)
            elif db_info.db_type == 'mysql':
                result = await self._check_mysql(db_info, timeout_sec)
            elif db_info.db_type == 'postgresql':
                result = await self._check_postgresql(db_info, timeout_sec)
            else:
                raise ValueError(f"Unsupported database type: {db_info.db_type}")
            
            # Calculate response time
            end_time = asyncio.get_event_loop().time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Update result with response time
            result.response_time_ms = response_time_ms
            
            # Check if response time is acceptable
            if result.is_available and response_time_ms > self.MAX_RESPONSE_TIME_MS:
                logger.warning(
                    f"⚠️ Database {db_info.db_type} is slow: "
                    f"{response_time_ms:.2f}ms (max: {self.MAX_RESPONSE_TIME_MS}ms)"
                )
            
            if not result.is_available:
                self.failed_count += 1
                logger.error(
                    f"❌ Database {db_info.db_type} unavailable: "
                    f"{result.error_message}"
                )
            else:
                logger.info(
                    f"✅ Database {db_info.db_type} available "
                    f"({response_time_ms:.2f}ms, v{result.version})"
                )
            
            return result
        
        except Exception as e:
            self.failed_count += 1
            logger.exception(f"❌ Database check failed: {str(e)}")
            
            end_time = asyncio.get_event_loop().time()
            response_time_ms = (end_time - start_time) * 1000
            
            return AvailabilityResult(
                is_available=False,
                db_type=db_info.db_type,
                response_time_ms=response_time_ms,
                version=None,
                error_message=str(e),
                timestamp=datetime.utcnow()
            )
    
    async def _check_oracle(
        self,
        db_info: DatabaseInfo,
        timeout_sec: int
    ) -> AvailabilityResult:
        """Check Oracle database availability"""
        try:
            import oracledb
            
            # Create connection string
            dsn = oracledb.makedsn(db_info.host, db_info.port, service_name=db_info.database)
            
            # Note: In real implementation, credentials would come from secure config
            # For now, this is a placeholder showing the structure
            connection = await asyncio.wait_for(
                asyncio.to_thread(
                    oracledb.connect,
                    dsn=dsn,
                    mode=oracledb.DEFAULT_AUTH
                ),
                timeout=timeout_sec
            )
            
            # Get version
            cursor = connection.cursor()
            await asyncio.to_thread(
                cursor.execute,
                "SELECT banner FROM v$version WHERE banner LIKE 'Oracle%'"
            )
            version_row = await asyncio.to_thread(cursor.fetchone)
            version = version_row[0] if version_row else "Unknown"
            
            await asyncio.to_thread(cursor.close)
            await asyncio.to_thread(connection.close)
            
            return AvailabilityResult(
                is_available=True,
                db_type='oracle',
                response_time_ms=0,  # Will be set by caller
                version=version,
                error_message=None,
                timestamp=datetime.utcnow()
            )
        
        except asyncio.TimeoutError:
            return AvailabilityResult(
                is_available=False,
                db_type='oracle',
                response_time_ms=0,
                version=None,
                error_message=f"Connection timeout after {timeout_sec} seconds",
                timestamp=datetime.utcnow()
            )
        except ImportError:
            return AvailabilityResult(
                is_available=False,
                db_type='oracle',
                response_time_ms=0,
                version=None,
                error_message="Oracle client library not installed (oracledb package required)",
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            return AvailabilityResult(
                is_available=False,
                db_type='oracle',
                response_time_ms=0,
                version=None,
                error_message=f"Connection failed: {str(e)}",
                timestamp=datetime.utcnow()
            )
    
    async def _check_mysql(
        self,
        db_info: DatabaseInfo,
        timeout_sec: int
    ) -> AvailabilityResult:
        """Check MySQL database availability"""
        try:
            import aiomysql
            
            # Create connection
            connection = await asyncio.wait_for(
                aiomysql.connect(
                    host=db_info.host,
                    port=db_info.port,
                    db=db_info.database,
                    connect_timeout=timeout_sec
                ),
                timeout=timeout_sec
            )
            
            # Get version
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT VERSION()")
                version_row = await cursor.fetchone()
                version = version_row[0] if version_row else "Unknown"
            
            connection.close()
            
            return AvailabilityResult(
                is_available=True,
                db_type='mysql',
                response_time_ms=0,  # Will be set by caller
                version=version,
                error_message=None,
                timestamp=datetime.utcnow()
            )
        
        except asyncio.TimeoutError:
            return AvailabilityResult(
                is_available=False,
                db_type='mysql',
                response_time_ms=0,
                version=None,
                error_message=f"Connection timeout after {timeout_sec} seconds",
                timestamp=datetime.utcnow()
            )
        except ImportError:
            return AvailabilityResult(
                is_available=False,
                db_type='mysql',
                response_time_ms=0,
                version=None,
                error_message="MySQL client library not installed (aiomysql package required)",
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            return AvailabilityResult(
                is_available=False,
                db_type='mysql',
                response_time_ms=0,
                version=None,
                error_message=f"Connection failed: {str(e)}",
                timestamp=datetime.utcnow()
            )
    
    async def _check_postgresql(
        self,
        db_info: DatabaseInfo,
        timeout_sec: int
    ) -> AvailabilityResult:
        """Check PostgreSQL database availability"""
        try:
            import asyncpg
            
            # Create connection
            connection = await asyncio.wait_for(
                asyncpg.connect(
                    host=db_info.host,
                    port=db_info.port,
                    database=db_info.database,
                    timeout=timeout_sec
                ),
                timeout=timeout_sec
            )
            
            # Get version
            version = await connection.fetchval("SELECT version()")
            
            await connection.close()
            
            return AvailabilityResult(
                is_available=True,
                db_type='postgresql',
                response_time_ms=0,  # Will be set by caller
                version=version,
                error_message=None,
                timestamp=datetime.utcnow()
            )
        
        except asyncio.TimeoutError:
            return AvailabilityResult(
                is_available=False,
                db_type='postgresql',
                response_time_ms=0,
                version=None,
                error_message=f"Connection timeout after {timeout_sec} seconds",
                timestamp=datetime.utcnow()
            )
        except ImportError:
            return AvailabilityResult(
                is_available=False,
                db_type='postgresql',
                response_time_ms=0,
                version=None,
                error_message="PostgreSQL client library not installed (asyncpg package required)",
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            return AvailabilityResult(
                is_available=False,
                db_type='postgresql',
                response_time_ms=0,
                version=None,
                error_message=f"Connection failed: {str(e)}",
                timestamp=datetime.utcnow()
            )
    
    def get_stats(self) -> dict:
        """Get validation statistics"""
        return {
            'total_checks': self.check_count,
            'failed_checks': self.failed_count,
            'success_rate': (
                (self.check_count - self.failed_count) / self.check_count * 100
                if self.check_count > 0 else 0
            )
        }

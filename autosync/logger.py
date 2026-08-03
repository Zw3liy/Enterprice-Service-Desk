"""
autosync/logger.py

Enterprise Logging System

Part 1/3

Features:
- Logger configuration
- Console logging
- File logging
- Log levels
- Structured formatting
- Logger factory

Used by:
- autosync engine
- scanner
- synchronizer
- backup manager
- utils

Author:
Enterprise AutoSync System
"""


from __future__ import annotations


import json
import logging
import os

from pathlib import Path
from datetime import datetime, timezone
from typing import (
    Any,
    Dict,
    Optional,
    Union,
)


# ============================================================
# LOGGER CONSTANTS
# ============================================================

LOGGER_NAME = "autosync"

LOGGER_VERSION = "1.0.0"


DEFAULT_LOG_LEVEL = logging.INFO


DEFAULT_LOG_DIRECTORY = "logs"


DEFAULT_LOG_FILE = "autosync.log"


DEFAULT_ENCODING = "utf-8"



# ============================================================
# LOG LEVELS
# ============================================================

LOG_LEVELS = {

    "debug": logging.DEBUG,

    "info": logging.INFO,

    "warning": logging.WARNING,

    "error": logging.ERROR,

    "critical": logging.CRITICAL,

}



def resolve_log_level(
    level: Union[str, int],
) -> int:
    """
    Convert log level name into logging constant.
    """

    if isinstance(level, int):

        return level


    return LOG_LEVELS.get(
        str(level).lower(),
        DEFAULT_LOG_LEVEL,
    )



# ============================================================
# TIME HELPERS
# ============================================================

def utc_time() -> str:
    """
    Generate UTC timestamp.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()



# ============================================================
# LOG FORMATTER
# ============================================================

class EnterpriseFormatter(
    logging.Formatter
):
    """
    Enterprise log formatter.

    Format:

    timestamp
    level
    logger
    message

    """


    def format(
        self,
        record: logging.LogRecord,
    ) -> str:


        timestamp = utc_time()


        return (
            f"{timestamp} | "
            f"{record.levelname:<8} | "
            f"{record.name} | "
            f"{record.getMessage()}"
        )



# ============================================================
# JSON FORMATTER
# ============================================================

class JSONFormatter(
    logging.Formatter
):
    """
    Structured JSON log formatter.
    """


    def format(
        self,
        record: logging.LogRecord,
    ) -> str:


        payload = {

            "timestamp":
                utc_time(),

            "level":
                record.levelname,

            "logger":
                record.name,

            "message":
                record.getMessage(),

        }


        if record.exc_info:

            payload["exception"] = (
                self.formatException(
                    record.exc_info
                )
            )


        return json.dumps(
            payload,
            ensure_ascii=False,
        )



# ============================================================
# DIRECTORY HELPERS
# ============================================================

def ensure_log_directory(
    directory: Union[str, Path],
) -> Path:
    """
    Create logging directory.
    """

    directory = Path(directory)


    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


    return directory



# ============================================================
# HANDLER CREATION
# ============================================================

def create_console_handler(
    level: int = DEFAULT_LOG_LEVEL,
) -> logging.Handler:
    """
    Create console logger.
    """

    handler = logging.StreamHandler()


    handler.setLevel(
        level
    )


    handler.setFormatter(
        EnterpriseFormatter()
    )


    return handler



def create_file_handler(
    filename: Union[str, Path],
    level: int = DEFAULT_LOG_LEVEL,
) -> logging.Handler:
    """
    Create file logger.
    """

    filename = Path(filename)


    ensure_log_directory(
        filename.parent
    )


    handler = logging.FileHandler(
        filename,
        encoding=DEFAULT_ENCODING,
    )


    handler.setLevel(
        level
    )


    handler.setFormatter(
        EnterpriseFormatter()
    )


    return handler



def create_json_file_handler(
    filename: Union[str, Path],
    level: int = DEFAULT_LOG_LEVEL,
) -> logging.Handler:
    """
    Create JSON log handler.
    """

    filename = Path(filename)


    ensure_log_directory(
        filename.parent
    )


    handler = logging.FileHandler(
        filename,
        encoding=DEFAULT_ENCODING,
    )


    handler.setLevel(
        level
    )


    handler.setFormatter(
        JSONFormatter()
    )


    return handler



# ============================================================
# LOGGER FACTORY
# ============================================================

def create_logger(
    name: str = LOGGER_NAME,
    level: Union[str, int] = DEFAULT_LOG_LEVEL,
    log_file: Optional[
        Union[str, Path]
    ] = None,
    json_logs: bool = False,
) -> logging.Logger:
    """
    Create enterprise logger.

    """

    logger = logging.getLogger(
        name
    )


    logger.setLevel(
        resolve_log_level(level)
    )


    logger.propagate = False



    if logger.handlers:

        return logger



    logger.addHandler(
        create_console_handler(
            resolve_log_level(level)
        )
    )



    if log_file:

        if json_logs:

            logger.addHandler(
                create_json_file_handler(
                    log_file,
                    resolve_log_level(level),
                )
            )

        else:

            logger.addHandler(
                create_file_handler(
                    log_file,
                    resolve_log_level(level),
                )
            )



    return logger

# ============================================================
# ROTATING LOG HANDLERS
# ============================================================

from logging.handlers import (
    RotatingFileHandler,
    TimedRotatingFileHandler,
)



def create_rotating_file_handler(
    filename: Union[str, Path],
    level: int = DEFAULT_LOG_LEVEL,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 10,
) -> logging.Handler:
    """
    Create rotating file logger.

    Rotation:
    - max file size
    - keeps backups

    Default:
    - 10MB files
    - 10 backups
    """

    filename = Path(filename)


    ensure_log_directory(
        filename.parent
    )


    handler = RotatingFileHandler(
        filename,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=DEFAULT_ENCODING,
    )


    handler.setLevel(
        level
    )


    handler.setFormatter(
        EnterpriseFormatter()
    )


    return handler



def create_daily_rotating_handler(
    filename: Union[str, Path],
    level: int = DEFAULT_LOG_LEVEL,
    backup_count: int = 30,
) -> logging.Handler:
    """
    Create daily rotating logger.

    Keeps:
    - previous 30 days
    """

    filename = Path(filename)


    ensure_log_directory(
        filename.parent
    )


    handler = TimedRotatingFileHandler(
        filename,
        when="midnight",
        interval=1,
        backupCount=backup_count,
        encoding=DEFAULT_ENCODING,
    )


    handler.setLevel(
        level
    )


    handler.setFormatter(
        EnterpriseFormatter()
    )


    return handler



# ============================================================
# STRUCTURED EVENTS
# ============================================================

class LogEvent:
    """
    Structured enterprise log event.

    Used for:
    - sync events
    - backups
    - file operations
    - audit records
    """


    def __init__(
        self,
        event: str,
        message: str,
        level: str = "info",
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ):

        self.event = event

        self.message = message

        self.level = level

        self.metadata = (
            metadata or {}
        )


        self.timestamp = utc_time()



    def to_dict(
        self,
    ) -> Dict[str, Any]:
        """
        Convert event to dictionary.
        """

        return {

            "timestamp":
                self.timestamp,

            "event":
                self.event,

            "level":
                self.level,

            "message":
                self.message,

            "metadata":
                self.metadata,

        }



    def to_json(
        self,
    ) -> str:
        """
        Convert event to JSON.
        """

        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
        )



# ============================================================
# EVENT LOGGER
# ============================================================

def log_event(
    logger: logging.Logger,
    event: LogEvent,
) -> None:
    """
    Write structured event.
    """

    level = resolve_log_level(
        event.level
    )


    logger.log(
        level,
        event.to_json(),
    )



# ============================================================
# AUDIT LOGGING
# ============================================================

class AuditLogger:
    """
    Enterprise audit logger.

    Tracks:
    - user actions
    - sync operations
    - system changes
    """


    def __init__(
        self,
        logger: logging.Logger,
    ):

        self.logger = logger



    def record(
        self,
        action: str,
        user: str = "system",
        details: Optional[
            Dict[str, Any]
        ] = None,
    ) -> None:
        """
        Record audit event.
        """

        event = LogEvent(

            event="audit",

            message=action,

            metadata={

                "user": user,

                "details":
                    details or {},

            },

        )


        log_event(
            self.logger,
            event,
        )



# ============================================================
# SYNC EVENT LOGGING
# ============================================================

class SyncLogger:
    """
    Specialized AutoSync logger.

    Tracks:
    - file creation
    - modification
    - deletion
    - synchronization
    """


    def __init__(
        self,
        logger: logging.Logger,
    ):

        self.logger = logger



    def file_created(
        self,
        path: Union[str, Path],
    ) -> None:

        self._write(

            "file_created",

            f"Created file: {path}",

            {
                "path":
                    str(path)
            }

        )



    def file_modified(
        self,
        path: Union[str, Path],
    ) -> None:

        self._write(

            "file_modified",

            f"Modified file: {path}",

            {
                "path":
                    str(path)
            }

        )



    def file_deleted(
        self,
        path: Union[str, Path],
    ) -> None:

        self._write(

            "file_deleted",

            f"Deleted file: {path}",

            {
                "path":
                    str(path)
            }

        )



    def sync_started(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
    ) -> None:

        self._write(

            "sync_started",

            "Synchronization started",

            {

                "source":
                    str(source),

                "destination":
                    str(destination),

            }

        )



    def sync_completed(
        self,
        files: int,
    ) -> None:

        self._write(

            "sync_completed",

            "Synchronization completed",

            {
                "files":
                    files
            }

        )



    def _write(
        self,
        event: str,
        message: str,
        metadata: Dict[str, Any],
    ):

        log_event(

            self.logger,

            LogEvent(

                event,

                message,

                metadata=metadata,

            ),

        )



# ============================================================
# EXCEPTION LOGGING
# ============================================================

def log_exception(
    logger: logging.Logger,
    exception: Exception,
    context: Optional[str] = None,
) -> None:
    """
    Log exceptions with context.
    """

    metadata = {

        "exception_type":
            type(exception).__name__,

        "exception":
            str(exception),

    }


    if context:

        metadata["context"] = context



    event = LogEvent(

        event="exception",

        message="Unhandled exception",

        level="error",

        metadata=metadata,

    )


    log_event(
        logger,
        event,
    )



def exception_handler(
    logger: logging.Logger,
):
    """
    Decorator for automatic exception logging.

    Example:

        @exception_handler(logger)
        def process():
            ...
    """


    def decorator(function):


        def wrapper(
            *args,
            **kwargs,
        ):

            try:

                return function(
                    *args,
                    **kwargs,
                )


            except Exception as exc:

                log_exception(
                    logger,
                    exc,
                    function.__name__,
                )

                raise


        return wrapper

# ============================================================
# PERFORMANCE TRACKING
# ============================================================

import time
from functools import wraps



class PerformanceTimer:
    """
    Enterprise performance timer.

    Tracks:
    - execution duration
    - operation name
    - metadata
    """

    def __init__(
        self,
        operation: str,
        logger: Optional[logging.Logger] = None,
    ):

        self.operation = operation

        self.logger = logger

        self.start_time = None

        self.end_time = None

        self.duration = None



    def start(self):
        """
        Start timer.
        """

        self.start_time = time.perf_counter()

        return self



    def stop(self):
        """
        Stop timer.
        """

        self.end_time = time.perf_counter()


        if self.start_time:

            self.duration = (
                self.end_time -
                self.start_time
            )


        if self.logger:

            self.logger.info(
                f"Operation '{self.operation}' completed in "
                f"{self.duration:.4f}s"
            )


        return self.duration



    def __enter__(self):

        return self.start()



    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):

        self.stop()



# ============================================================
# PERFORMANCE DECORATOR
# ============================================================

def track_performance(
    logger: Optional[logging.Logger] = None,
):
    """
    Decorator for measuring function runtime.

    Example:

        @track_performance(logger)
        def sync_files():
            ...
    """

    def decorator(function):


        @wraps(function)
        def wrapper(
            *args,
            **kwargs,
        ):

            timer = PerformanceTimer(
                function.__name__,
                logger,
            )


            timer.start()


            try:

                return function(
                    *args,
                    **kwargs,
                )


            finally:

                timer.stop()



        return wrapper


    return decorator



# ============================================================
# OPERATION TRACKING
# ============================================================

class OperationTracker:
    """
    Tracks long-running operations.

    Used for:
    - sync jobs
    - backups
    - scans
    """


    def __init__(
        self,
        logger: logging.Logger,
    ):

        self.logger = logger


        self.active_operations = {}



    def start(
        self,
        operation_id: str,
        name: str,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ):

        self.active_operations[
            operation_id
        ] = {

            "name":
                name,

            "started":
                utc_time(),

            "metadata":
                metadata or {},

        }


        self.logger.info(
            f"Started operation: {name}"
        )



    def complete(
        self,
        operation_id: str,
        success: bool = True,
    ):

        operation = (
            self.active_operations.pop(
                operation_id,
                None,
            )
        )


        if not operation:

            return



        status = (
            "completed"
            if success
            else
            "failed"
        )


        self.logger.info(
            f"Operation {status}: "
            f"{operation['name']}"
        )



    def active(
        self,
    ) -> Dict[str, Any]:
        """
        Return active operations.
        """

        return self.active_operations.copy()



# ============================================================
# LOGGER MANAGER
# ============================================================

class LoggerManager:
    """
    Singleton enterprise logger manager.

    Provides centralized access to:

    - application logger
    - audit logger
    - sync logger
    - operation tracker
    """

    _instance = None



    def __new__(
        cls,
        *args,
        **kwargs,
    ):

        if cls._instance is None:

            cls._instance = super(
                LoggerManager,
                cls
            ).__new__(
                cls
            )

        return cls._instance



    def __init__(
        self,
    ):

        if hasattr(
            self,
            "_initialized",
        ):

            return


        self.logger = None

        self.audit = None

        self.sync = None

        self.operations = None


        self._initialized = True



    def initialize(
        self,
        name: str = LOGGER_NAME,
        level: Union[str, int] = DEFAULT_LOG_LEVEL,
        log_file: Optional[
            Union[str, Path]
        ] = None,
    ):

        self.logger = create_logger(
            name=name,
            level=level,
            log_file=log_file,
        )


        self.audit = AuditLogger(
            self.logger
        )


        self.sync = SyncLogger(
            self.logger
        )


        self.operations = OperationTracker(
            self.logger
        )


        return self.logger



    def get_logger(
        self,
    ) -> logging.Logger:
        """
        Return active logger.
        """

        if self.logger is None:

            self.initialize()


        return self.logger



# ============================================================
# GLOBAL LOGGER INSTANCE
# ============================================================

logger_manager = LoggerManager()



def get_logger(
    name: str = LOGGER_NAME,
) -> logging.Logger:
    """
    Retrieve application logger.
    """

    return logger_manager.get_logger()



def initialize_logging(
    level: Union[str, int] = DEFAULT_LOG_LEVEL,
    log_file: Optional[
        Union[str, Path]
    ] = None,
):
    """
    Initialize global logging system.
    """

    return logger_manager.initialize(
        level=level,
        log_file=log_file,
    )



# ============================================================
# MODULE EXPORTS
# ============================================================

__all__ = [

    # constants
    "LOGGER_NAME",
    "LOGGER_VERSION",

    # factory
    "create_logger",
    "get_logger",
    "initialize_logging",

    # formatters
    "EnterpriseFormatter",
    "JSONFormatter",

    # handlers
    "create_file_handler",
    "create_rotating_file_handler",
    "create_daily_rotating_handler",

    # events
    "LogEvent",
    "log_event",

    # audit
    "AuditLogger",

    # sync
    "SyncLogger",

    # exceptions
    "log_exception",
    "exception_handler",

    # performance
    "PerformanceTimer",
    "track_performance",

    # operations
    "OperationTracker",

    # manager
    "LoggerManager",
]

    return decorator
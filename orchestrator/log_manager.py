"""
Log Manager - Manages structured logging for workflow execution.

Provides:
- Rotating file handlers for executions and errors
- Structured JSON log format
- Query interface for recent logs
- Separate loggers for different log types
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime


class LogManager:
    """Manages structured logging for workflow execution."""

    def __init__(self, log_dir: str = "logs"):
        """Initialize Log Manager.

        Args:
            log_dir: Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup loggers
        self.execution_logger = self._setup_logger(
            "executions",
            self.log_dir / "executions.log"
        )
        self.error_logger = self._setup_logger(
            "errors",
            self.log_dir / "errors.log",
            level=logging.ERROR
        )

    def _setup_logger(
        self,
        name: str,
        log_file: Path,
        level: int = logging.INFO
    ) -> logging.Logger:
        """Setup a rotating file logger.

        Args:
            name: Logger name
            log_file: Path to log file
            level: Logging level

        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Remove existing handlers to avoid duplicates
        logger.handlers = []

        # Rotating file handler (10MB max, keep 5 backups)
        handler = RotatingFileHandler(
            str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )

        # JSON formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

        # Prevent propagation to root logger
        logger.propagate = False

        return logger

    # ========================================
    # Logging Operations
    # ========================================

    def log_execution_start(
        self,
        execution_id: str,
        agent_id: str,
        user_input: str,
        **kwargs
    ):
        """Log execution start.

        Args:
            execution_id: Execution ID
            agent_id: Agent being executed
            user_input: User task input
            **kwargs: Additional context
        """
        log_data = {
            "event": "execution_start",
            "execution_id": execution_id,
            "agent_id": agent_id,
            "user_input": user_input[:200] if user_input else "",  # Truncate
            **kwargs
        }
        self.execution_logger.info(json.dumps(log_data))

    def log_execution_complete(
        self,
        execution_id: str,
        agent_id: str,
        status: str,
        tokens_in: int,
        tokens_out: int,
        **kwargs
    ):
        """Log execution completion.

        Args:
            execution_id: Execution ID
            agent_id: Agent ID
            status: completed|failed
            tokens_in: Input tokens
            tokens_out: Output tokens
            **kwargs: Additional context
        """
        log_data = {
            "event": "execution_complete",
            "execution_id": execution_id,
            "agent_id": agent_id,
            "status": status,
            "tokens": {
                "input": tokens_in,
                "output": tokens_out,
                "total": tokens_in + tokens_out
            },
            **kwargs
        }
        self.execution_logger.info(json.dumps(log_data))

    def log_execution_error(
        self,
        execution_id: str,
        agent_id: str,
        error: str,
        traceback: Optional[str] = None,
        **kwargs
    ):
        """Log execution error.

        Args:
            execution_id: Execution ID
            agent_id: Agent ID
            error: Error message
            traceback: Full traceback
            **kwargs: Additional context
        """
        log_data = {
            "event": "execution_error",
            "execution_id": execution_id,
            "agent_id": agent_id,
            "error": error,
            "traceback": traceback,
            **kwargs
        }
        self.error_logger.error(json.dumps(log_data))

    def log_validation(
        self,
        execution_id: str,
        agent_id: str,
        status: str,
        errors: List[dict],
        **kwargs
    ):
        """Log validation result.

        Args:
            execution_id: Execution ID
            agent_id: Agent ID
            status: pass|fail|warn
            errors: List of validation errors
            **kwargs: Additional context
        """
        log_data = {
            "event": "validation",
            "execution_id": execution_id,
            "agent_id": agent_id,
            "status": status,
            "error_count": len(errors),
            "errors": errors,
            **kwargs
        }

        if status == "fail":
            self.error_logger.error(json.dumps(log_data))
        else:
            self.execution_logger.info(json.dumps(log_data))

    # ========================================
    # Query Operations
    # ========================================

    def get_recent_logs(
        self,
        log_type: str = "executions",
        limit: int = 100
    ) -> List[str]:
        """Get recent log entries.

        Args:
            log_type: executions or errors
            limit: Max number of lines

        Returns:
            List of log lines
        """
        log_file = self.log_dir / f"{log_type}.log"
        if not log_file.exists():
            return []

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            return lines[-limit:]
        except Exception as e:
            return [f"Error reading log file: {e}"]

    def search_logs(
        self,
        pattern: str,
        log_type: str = "executions"
    ) -> List[str]:
        """Search logs for pattern.

        Args:
            pattern: String to search for
            log_type: executions or errors

        Returns:
            List of matching log lines
        """
        log_file = self.log_dir / f"{log_type}.log"
        if not log_file.exists():
            return []

        matches = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if pattern in line:
                        matches.append(line.strip())
        except Exception as e:
            return [f"Error searching log file: {e}"]

        return matches

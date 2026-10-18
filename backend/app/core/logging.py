import json
import logging
import logging.config
from datetime import UTC, datetime

_STANDARD_RECORD_KEYS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_KEYS and not key.startswith("_")
        }
        if extras:
            payload["extra"] = extras

        return json.dumps(payload, default=str, ensure_ascii=False)


class ColorFormatter(logging.Formatter):
    _COLORS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[1;31m",  # Bold Red
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Save the original levelname to avoid permanently modifying the record
        original_levelname = record.levelname

        # Colorize and pad the levelname to 8 characters for clean vertical alignment
        color = self._COLORS.get(record.levelno, self._RESET)
        record.levelname = f"{color}{original_levelname:<8}{self._RESET}"

        try:
            return super().format(record)
        finally:
            # Restore the original levelname
            record.levelname = original_levelname


def configure_logging(level: str = "INFO", *, json_logs: bool = False) -> None:
    formatter_name = "json" if json_logs else "color"

    formatters = {
        "json": {
            "()": JsonFormatter,
        },
        "color": {
            "()": ColorFormatter,
            # Note: MUST use 'fmt', not 'format', when instantiating via '()'
            "fmt": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": formatters,
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter_name,
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": getattr(logging, level.upper(), logging.INFO),
                "handlers": ["default"],
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default"],
                    "level": getattr(logging, level.upper(), logging.INFO),
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["default"],
                    "level": getattr(logging, level.upper(), logging.INFO),
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": getattr(logging, level.upper(), logging.INFO),
                    "propagate": False,
                },
            },
        }
    )

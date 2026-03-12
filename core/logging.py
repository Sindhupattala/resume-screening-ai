import logging
from datetime import datetime

class TimeZoneLogger:
    def __init__(self, logger_name: str = "HRBOT", log_level: int = logging.INFO):
        self.logger_name = logger_name
        self.log_level = log_level
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Configure and return a logger with local time timestamps."""
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(self.log_level)

        # Avoid duplicate handlers
        if logger.handlers:
            return logger

        # Formatter with local time
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Use local time via time.localtime
        formatter.converter = lambda sec: datetime.fromtimestamp(sec).timetuple() if sec else datetime.now().timetuple()

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def get_logger(self):
        """Return the configured logger instance."""
        return self.logger
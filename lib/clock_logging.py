import os
import logging
from logging.handlers import RotatingFileHandler
from lib.arg_parser import args


class DedupFilter(logging.Filter):
    """Suppress consecutive duplicate log messages; prefix the next distinct one with a count."""
    def __init__(self):
        super().__init__()
        self._last_msg = None
        self._suppressed = 0

    def filter(self, record):
        msg = record.getMessage()
        if msg == self._last_msg:
            self._suppressed += 1
            return False
        if self._suppressed:
            record.msg = f"[+{self._suppressed} suppressed dupes] {record.msg}"
            self._suppressed = 0
        self._last_msg = msg
        return True


class ClockLogger:
    """
    The ClockLogger class is responsible for setting up the logger used in the application.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        os.makedirs("cache", exist_ok=True)

        self.setup_file_handler()
        if args.v:
            self.setup_console_handler()

    def setup_file_handler(self):
        """
        Set up a file handler for the logger. The logs will be stored in 'cache/clock.log'.
        """
        f_handler = RotatingFileHandler(
            'cache/clock.log',
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
        )
        f_handler.setLevel(logging.INFO)
        f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        f_handler.setFormatter(f_format)
        f_handler.addFilter(DedupFilter())
        self.logger.addHandler(f_handler)

    def setup_console_handler(self):
        """
        Set up a console handler for the logger. The logs will be printed to the console.
        """
        c_handler = logging.StreamHandler()
        c_handler.setLevel(logging.INFO)
        c_format = logging.Formatter('%(levelname)s - %(message)s')
        c_handler.setFormatter(c_format)
        self.logger.addHandler(c_handler)

logger = ClockLogger().logger

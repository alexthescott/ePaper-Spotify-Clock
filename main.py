import logging
import sys
from lib.arg_parser import args
from lib.clock import Clock
from lib.clock_logging import logger


def _log_uncaught(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    sys.excepthook = _log_uncaught

    clock = Clock()
    if args.local or (clock.local_run and not args.clock):
        clock.build_image()
        clock.save_local_file()
    else:
        clock.tick_tock()

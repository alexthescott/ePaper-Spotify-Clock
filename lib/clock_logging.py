import logging
import os
from logging.handlers import RotatingFileHandler
from lib.arg_parser import args

# Create and set level of a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create stdout logging if -v is passed
if args.v:
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    logger.addHandler(c_handler)

os.makedirs("cache", exist_ok=True)

f_handler = RotatingFileHandler('cache/clock.log', maxBytes=2*1024*1024, backupCount=5)
f_handler.setLevel(logging.INFO)
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)

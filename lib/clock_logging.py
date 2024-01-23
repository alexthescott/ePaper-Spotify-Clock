import logging
import json
from lib.misc import Misc

misc = Misc()

# Create a custom logger
logger = logging.getLogger(__name__)

# Read the value from the cache/args_parse.json file
with open('cache/args_parse.json', 'r') as f:
    config = json.load(f)

verbose_logging = config['verbose_logging']

# Set level of logger
logger.setLevel(logging.INFO)

# Create handlers
if verbose_logging:
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    # Add handlers to the logger
    logger.addHandler(c_handler)

f_handler = logging.FileHandler('cache/clock.log')
f_handler.setLevel(logging.INFO)
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)

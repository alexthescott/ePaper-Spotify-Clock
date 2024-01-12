import logging
import argparse

# Create a custom logger
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
std_out_logging = parser.parse_args().v

# Set level of logger
logger.setLevel(logging.INFO)

# Create handlers
if std_out_logging:
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    # Add handlers to the logger
    logger.addHandler(c_handler)
f_handler = logging.FileHandler('clock.log')
f_handler.setLevel(logging.INFO)
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
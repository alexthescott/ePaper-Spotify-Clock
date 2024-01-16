import logging
import argparse
import json
import os
from lib.misc import Misc

misc = Misc()

parser = argparse.ArgumentParser()
parser.add_argument('-v', action='store_true', help='Enable Verbose Logging')
parser.add_argument('--clock', action='store_true', help='Enable clock')

args = parser.parse_args()
# Write the values to a JSON configuration file
if not os.path.exists("cache"):
    os.makedirs("cache")
with open('cache/args_parse.json', 'w') as f:
    json.dump({'verbose_logging': args.v, 'clock': args.clock}, f)

if __name__ == "__main__":
    from lib.clock import Clock
    logging.getLogger().setLevel(logging.INFO)
    clock = Clock()
    if clock.local_run and not args.clock:
        clock.build_image()
        clock.save_local_file()
    else:
        clock.tick_tock()
import logging
import argparse
import json
import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='store_true', help='Enable Verbose Logging')
    parser.add_argument('--clock', action='store_true', help='Enable clock')
    parser.add_argument('--local', action='store_true', help='Force write to test_output/')

    args = parser.parse_args()
    # Write the values to a JSON configuration file
    if not os.path.exists("cache"):
        os.makedirs("cache")
    with open('cache/args_parse.json', 'w') as f:
        json.dump({'verbose_logging': args.v, 'clock': args.clock, 'local': args.local}, f)

    from lib.misc import Misc
    from lib.clock import Clock
    misc = Misc()
    logging.getLogger().setLevel(logging.INFO)

    clock = Clock()
    if args.local or (clock.local_run and not args.clock):
        clock.build_image()
        clock.save_local_file()
    else:
        clock.tick_tock()
import logging
import argparse
from lib.clock import Clock

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--clock', action='store_true', help='Enable clock on unsupported machine ')
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)
    clock = Clock()
    if clock.local_run and not args.clock:
        clock.build_image()
        clock.save_local_file()
    else:
        clock.tick_tock()

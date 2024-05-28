import logging
from lib.arg_parser import args
from lib.clock import Clock

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)

    clock = Clock()
    if args.local or (clock.local_run and not args.clock):
        clock.build_image()
        clock.save_local_file()
    else:
        clock.tick_tock()

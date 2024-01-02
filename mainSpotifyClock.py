import logging
from lib.clock import Clock

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    clock = Clock()
    if False and clock.local_run:
        clock.build_image()
        clock.save_local_file()
    else:
        clock.tick_tock()

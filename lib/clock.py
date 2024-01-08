import pdb
import json
from time import time, sleep, strftime
from datetime import timedelta, datetime as dt
import logging
import logging
from logging.handlers import RotatingFileHandler

from lib.draw import Draw
from lib.weather import Weather
from lib.spotify_user import SpotifyUser
from lib.misc import Misc
from lib.json_io import LocalJsonIO
from lib.clock_logging import logger

class Clock:
    def __init__(self):
        # -------- Init --------
        self.local_run = False
        try:
            from waveshare_epd import epd4in2
        except ImportError:
            self.local_run = True

        logger.info("\t-- Clock Init --\n-----------------------------------------------------------------------------------------------------")
        self.load_display_settings()

        # Initialize Info/Drawing Libs/Users
        self.image_obj = Draw()
        self.weather = Weather()
        self.misc = Misc()
        self.ctx_io = LocalJsonIO()
        self.spotify_user_1 = SpotifyUser("Alex", single_user=self.single_user)
        self.ctx_type_1, self.ctx_title_1 = "", ""
        self.spotify_user_2 = (SpotifyUser("Emma", main=False) if not self.single_user else None)
        self.ctx_type_2, self.ctx_title_2 = "", ""

        # EPD vars/settings
        self.epd = epd4in2.EPD() if not self.local_run else None
        self.did_epd_init = False
        self.count_to_5 = 0  # count_to_5 is used to get weather every 5 minutes
        self.time_elapsed = 15.0
        self.old_time = None

        # Weather/Sunset vars
        self.weather_info = None
        self.sunset_info = None
        self.sunset_time_tuple = None

    def load_display_settings(self):
        with open("config/display_settings.json") as display_settings:
            display_settings = json.load(display_settings)
            self.single_user = display_settings["single_user"]
            self.sunset_flip = display_settings["sunset_flip"]
            self.twenty_four_hour_clock = display_settings["twenty_four_hour_clock"]
            self.partial_update = display_settings["partial_update"]
            self.time_on_right = display_settings["time_on_right"]

    def set_weather_and_sunset_info(self):
        self.weather_info, self.sunset_info = self.weather.get_weather_and_sunset_info()
        self.flip_to_dark = self.misc.has_sun_set(self.sunset_info, self.sunset_flip)

    def save_local_file(self):
        self.image_obj.save_png("{}".format(dt.now().strftime("%H:%M:%S")))
        self.image_obj.save_png("now")

    def tick_tock(self):
        while True:
            self.image_obj.clear_image()
            if self.weather_info is None or self.count_to_5 >= 4:
                self.set_weather_and_sunset_info()
            sec_left, time_str, date_str, old_time = self.get_time_from_date_time()
            logger.info("Time: {}".format(time_str))
            start = time() # Used to 'push' our clock timing forward to account for EPD time

            # If we have no context read, grab context our context.txt json file
            if all([self.ctx_type_1, self.ctx_title_1]) or all([self.ctx_type_2, self.ctx_title_2]):
                try:
                    fh = open("context.txt")
                    self.ctx_type_1, self.ctx_type_1, self.ctx_type_2, self.ctx_title_2 = self.ctx_io.read_json_ctx((self.ctx_type_1, self.ctx_title_1), (self.ctx_type_2, self.ctx_title_2))
                    fh.close()
                except:
                    print("context.txt doesn't exist")
            # Afterwords, if we have to write a new context to our context.txt json file, do so
            if (self.ctx_type_1 != "" and self.ctx_title_1 != "") or (self.ctx_type_2 != "" and self.ctx_title_2 != ""):
                self.ctx_io.write_json_ctx((self.ctx_type_1, self.ctx_title_1),(self.ctx_type_2, self.ctx_title_2))
            
            self.build_image()

            # Get 24H clock c_hour to determine sleep duration before refresh
            date = dt.now() + timedelta(seconds=self.time_elapsed)
            c_hour = int(date.strftime("%-H"))
            c_minute = int(date.strftime("%-M"))

            # from 2:01 - 5:59am, don't init the display, return from main, and have .sh script run again in 3 mins
            if 2 <= c_hour and c_hour <= 5:
                if self.did_epd_init:
                    # in sleep() from epd4in2.py, epdconfig.module_exit() is never called
                    # I hope this does not create long term damage 🤞
                    print("EPD Sleep(ish) ....")
                    break
                else:
                    print("Don't Wake")
                    break
            elif not self.did_epd_init:
                logger.info("Initializing EPD...")
                if self.epd:
                    self.epd.init()
                    self.epd.Clear()
                else:
                    self.save_local_file()
                self.did_epd_init = True

            if self.did_epd_init:
                if self.epd:
                    image_buffer = self.epd.getbuffer(self.image_obj.get_image_obj())
                    logger.info("\tDrawing Image to EPD")
                    self.epd.display(image_buffer)
                else:
                    logger.info("\tSaving Image Locally")
                    self.save_local_file()

            # Look @ start variable above. find out how long it takes to compute our image
            stop = time()
            self.time_elapsed = stop - start

            remaining_time = sec_left - self.time_elapsed
            remaining_time = 60 if remaining_time < 0 else remaining_time

            if 5 < c_hour and c_hour < 24:
                # 6:00am - 12:59pm update screen every 3 minutes
                logger.info("\t{}\tseconds per loop\tsleeping for {} seconds".format(round(self.time_elapsed, 2), int(remaining_time/1+120)))
                # if we do partial updates and darkmode, you get a worrisome zebra stripe artifact on the EPD
                if self.partial_update and not self.flip_to_dark:
                    # Create new time image, push to display, full update after 2 partials
                    partial_update_count = 0
                    while partial_update_count < 3:
                        date = dt.now()
                        sec_left = 62 - int(date.strftime("%S"))

                        if partial_update_count < 2:
                            logger.info("\t{}s sleep, partial_update".format(round(sec_left, 2)))
                            sleep(sec_left)
                        else:
                            logger.info("\t{}\tseconds per loop\tsleeping for {} seconds".format(round(self.time_elapsed, 2), int(remaining_time/1+120)))
                            sleep(sec_left - self.time_elapsed)

                        if sec_left > 5 and partial_update_count < 2:
                            date = dt.now()
                            time_str = date.strftime("%-H:%M") if self.twenty_four_hour_clock else date.strftime("%-I:%M") + date.strftime("%p").lower()
                            logger.info("\ttimestr:{}".format(time_str))
                            time_image, time_width = self.image_obj.create_time_text(time_str, self.weather_info)
                            if self.epd:
                                if self.time_on_right:
                                    self.epd.EPD_4IN2_PartialDisplay(self.image_obj.WIDTH-5-time_width, 245, self.image_obj.WIDTH-5, 288, self.epd.getbuffer(time_image))
                                else:
                                    self.epd.EPD_4IN2_PartialDisplay(5, 245, 5+time_width, 288, self.epd.getbuffer(time_image))
                        partial_update_count += 1
                else:
                    sleep(remaining_time + 120)
            elif c_hour < 2:
                # 12:00am - 1:59am update screen every 5ish minutes
                logger.info("\t", round(self.time_elapsed, 2), "\tseconds per loop\t", "sleeping for {} seconds".format(int(remaining_time+240)))
                sleep(remaining_time+240)

            # Increment counter for Weather requests
            self.count_to_5 = 0 if self.count_to_5 == 4 else self.count_to_5 + 1

    def build_image(self):
        if self.weather_info is None:
            self.set_weather_and_sunset_info()
        self.image_obj.draw_date_time_temp(self.weather_info)
        self.image_obj.draw_border_lines()

        # --- Spotify User 1 ---
        track_1, artist_1, time_since_1, tmp_ctx_type_1, tmp_ctn_name_1, track_image_link, album_name_1 = self.spotify_user_1.get_spotipy_info()
        track_line_count, track_text_size = self.image_obj.draw_track_text(track_1, 207, 26)
        self.image_obj.draw_artist_text(artist_1, track_line_count, track_text_size, 207, 26)

        ctx_type_1 = tmp_ctx_type_1 if tmp_ctx_type_1 != "" else ctx_type_1
        ctx_title_1 = tmp_ctn_name_1 if tmp_ctn_name_1 != "" else ctx_title_1
        self.image_obj.draw_spot_context(ctx_type_1, ctx_title_1, 227, 204)

        name_width_1, name_height_1 = self.image_obj.draw_name(self.spotify_user_1.name, 210, 0)
        self.image_obj.draw_user_time_ago(time_since_1, 220 + name_width_1, name_height_1 // 2)

        # --- Spotify User 2 or Album Art Display ---
        if not self.single_user:
            track_2, artist_2, time_since_2, tmp_ctx_type_2, tmp_ctn_name_2, track_image_link, album_name_2 = self.spotify_user_2.get_spotipy_info()
            track_line_count, track_text_size = self.image_obj.draw_track_text(track_1, 5, 26)
            self.image_obj.draw_artist_text(artist_2, track_line_count, track_text_size, 5, 26)

            ctx_type_2 = tmp_ctx_type_2 if tmp_ctx_type_2 != "" else ctx_type_2
            ctx_title_2 = tmp_ctn_name_2 if tmp_ctn_name_2 != "" else ctx_title_2
            self.image_obj.draw_spot_context(ctx_type_2, ctx_title_2, 25, 204)

            name_width_2, name_height_2 = self.image_obj.draw_name(self.spotify_user_2.name, 8, 0)
            self.image_obj.draw_user_time_ago(time_since_1, 18 + name_width_2, name_height_2 // 2)
        else:
            self.misc.get_album_art(track_image_link)
            self.image_obj.draw_album_image(self.flip_to_dark)
            self.image_obj.draw_spot_context("album", album_name_1, 25, 204)

        # -------- Dark Mode --------
        # Dark mode ~25 minutes after the sunsets. Determined by the bool sunset_flip
        if self.flip_to_dark:
            self.image_obj.dark_mode_flip()

    def get_time_from_date_time(self):
        """Return time information from datetime including seconds, time, date, and the current_minute of update.

        Parameters:
            old_min: used to ensure a proper update interval
        Returns:
            sec_left: used to know how long we should sleep for before next update on the current_minute
            time_str: time text to be displayed
            date_str: date text to be displayed
            new_min: will become the old_min var in next call for proper interval
        """
        date = dt.now() + timedelta(seconds=self.time_elapsed)
        am_pm = date.strftime("%p")
        hour = int(date.strftime("%-H"))
        new_min = int(date.strftime("%M")[-1])

        # Here we make some considerations so the screen isn't updated too frequently
        # We air on the side of caution, and would rather add an additional current_minute than shrink by a current_minute
        if self.old_time is not None and (5 < hour and hour < 24):
            # 6:00am - 11:59pm update screen every 3 mins
            while int(abs(self.old_time - new_min)) < 3:
                date = dt.now() + timedelta(seconds=self.time_elapsed)
                new_min = int(date.strftime("%M")[-1])
                sleep(2)
        # 12:00am - 1:59am update screen every 5 mins at least
        elif self.old_time is not None and (hour < 2):
            while int(abs(self.old_time - new_min)) < 5:
                date = dt.now() + timedelta(seconds=self.time_elapsed)
                new_min = int(date.strftime("%M")[-1])
                sleep(2)
        # 2:00am - 5:59am check time every 15ish minutes, granularity here is not paramount
        sec_left = 60 - int(date.strftime("%S"))
        date_str, am_pm = date.strftime("%a, %b %-d"), date.strftime("%p")

        time_str = date.strftime("%-H:%M") if self.twenty_four_hour_clock else date.strftime("%-I:%M") + am_pm.lower()
        return sec_left, time_str, date_str, int(new_min)

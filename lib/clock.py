import json
import re
import sys
import threading
from time import time, sleep
from datetime import timedelta, datetime as dt
from typing import NoReturn, Optional, Tuple

from lib.display_settings import DisplaySettings, display_settings
from lib.draw import Draw
from lib.weather import Weather, WeatherInfo, SunsetInfo, FourHourForecast
from lib.spotify_user import SpotifyUser
from lib.misc import Misc
from lib.clock_logging import logger

class Clock:
    """
    Clock updates the screen with the current Spotify info, time, date, and weather on a regular loop.
    Clock caches the local context of the Spotify user, and will only update the context if the user has changed.
    """
    def __init__(self) -> None:
        logger.info("\n\t-- Clock Init --\n-----------------------------------------------------------------------------------------------------")
        self.local_run: bool = False
        try:
            from waveshare_epd import epd4in2_V2, epd4in2
        except ImportError:
            self.local_run = True

        # EPD vars/settings
        self.ds: DisplaySettings = display_settings
        self.epd: Optional[None] = None
        if not self.local_run:
            self.epd = epd4in2_V2.EPD() if self.ds.use_epd_lib_V2 else epd4in2.EPD()
        self.did_epd_init: bool = False
        self.loops_until_weather_refresh: int = 5
        self.weather_refresh_loop_count: int = 0
        self.time_elapsed: float = 15.0
        self.old_time: Optional[dt] = None
        self.flip_to_dark: bool = self.ds.always_dark_mode

        # Weather/Sunset vars
        self.weather_info: Optional[WeatherInfo] = None
        self.sunset_info: Optional[SunsetInfo] = None
        self.four_hour_forecast: Optional[FourHourForecast] = None
        self.get_new_album_art: Optional[bool] = False if self.ds.single_user else None
        self.draw_detailed_weather: bool = False

        # Initialize Info/Drawing Libs/Users
        self.image_obj: Draw = Draw(self.local_run)
        self.weather: Weather = Weather()
        self.misc: Misc = Misc()
        self.spotify_user_1: SpotifyUser = SpotifyUser(self.ds.name_1, self.ds.single_user)
        self.track_1 = ""
        self.artist_1 = ""
        self.time_since_1 = ""
        self.track_image_link = ""
        self.ctx_type_1: str = ""
        self.ctx_title_1: str = ""
        self.old_album_name1: str = ""
        self.album_name_1: str = ""
        self.spotify_user_2: Optional[SpotifyUser] = SpotifyUser(self.ds.name_2, self.ds.single_user, main_user=False) if not self.ds.single_user else None
        self.ctx_type_2: str = ""
        self.ctx_title_2: str = ""

    def set_weather(self) -> None:
        """
        Sets the weather information for the clock.
        """
        self.weather_info: WeatherInfo = self.weather.get_current_temperature_info()

    def set_sunset_info(self) -> None:
        """
        Sets the sunset information for the clock.
        """
        self.sunset_info: SunsetInfo = self.weather.get_sunset_info()
        flip_to_dark_before: bool = self.flip_to_dark
        if self.ds.sunset_flip:
            self.flip_to_dark = self.misc.has_sun_set(self.sunset_info, self.ds.sunset_flip) or self.ds.always_dark_mode
            if not flip_to_dark_before and self.flip_to_dark:
                self.get_new_album_art = True

    def set_four_hour_forecast(self) -> None:
        """
        Sets the 4-hour forecast for the clock.
        """
        self.four_hour_forecast: FourHourForecast = self.weather.get_four_hour_forecast()

    def save_local_file(self) -> None:
        """
        Saves the image object "clock_output.png" for later reference
        """
        self.image_obj.save_png("clock_output")
        
    def init_epd(self) -> NoReturn:
        """
        Used to initialize the EPD display within a thread to prevent blocking the main loop.
        """
        try:
            self.epd.init()
        except RuntimeError as e:
            logger.error("Failed to init EPD: %s", e)

    def tick_tock(self):
        """
        Main loop for the clock functionality.
        continuously updates the clock display and handles various operations based on the current time.
        """
        while True:
            # Get 24H clock c_hour to determine sleep duration before refresh
            date = dt.now() + timedelta(seconds=self.time_elapsed)
            c_hour = int(date.strftime("%-H"))
            # c_minute = int(date.strftime("%-M")) # in case we need it later
            start = time() # Used to 'push' our clock timing forward to account for EPD time

            # from 2:01 - 5:59am, don't init the display, return from main, and have .sh script run again in 3 mins
            if 2 <= c_hour <= 5:
                if self.did_epd_init:
                    self.epd.sleep()
                    self.did_epd_init = False
                    logger.info("epd.sleep()....")
                else:
                    logger.info("still sleeping... %s", dt.now().strftime('%-I:%M%p'))
                    sleep(55)
                break
            elif not self.did_epd_init:
                if not self.local_run:
                    # try initing the EPD for a total of 45 seconds
                    thread = threading.Thread(target=self.init_epd)
                    thread.start()
                    thread.join(45)
                    if thread.is_alive():
                        logger.error("Failed to init EPD in 45 seconds")
                        print("Failed to initialize EPD within 45 seconds, exiting program.", file=sys.stdout)
                        sys.exit(1)
                    else:
                        logger.info("EPD Initialized")
                    
                    if self.ds.four_gray_scale:
                        logger.info("Initializing EPD 4Gray...")
                        self.epd.Init_4Gray()
                    elif self.ds.partial_update:
                        logger.info("Initializing Partial EPD...")
                        self.epd.init_fast(self.epd.Seconds_1_5S)
                self.did_epd_init = True

            self.image_obj.clear_image()
            if self.weather_info is None or self.weather_refresh_loop_count >= self.loops_until_weather_refresh:
                self.set_weather()
                self.set_sunset_info()
                if self.ds.detailed_weather_forecast and self.draw_detailed_weather:
                    self.set_four_hour_forecast()
            sec_left, time_str = self.get_time_from_date_time()
            logger.info("Time: %s", time_str)

            self.build_image(time_str)

            if self.did_epd_init:
                if not self.local_run:
                    logger.info("\tDrawing Image to EPD")
                    if self.ds.four_gray_scale:
                        self.epd.display_4Gray(self.epd.getbuffer_4Gray(self.image_obj.get_image_obj()))
                    else:
                        self.epd.display(self.epd.getbuffer(self.image_obj.get_image_obj()))
                    if self.ds.sleep_epd and (not self.ds.partial_update or self.flip_to_dark):
                        logger.info("\tSleeping EPD")
                        self.epd.sleep()
                        self.did_epd_init = False
                else:
                    logger.info("\tSaving Image Locally")
                    self.save_local_file()

            # Look @ start variable above. find out how long it takes to compute our image
            stop = time()

            self.time_elapsed = stop - start
            remaining_time = sec_left - self.time_elapsed
            if 5 < c_hour and c_hour < 23:
                # 6:00am - 10:59pm update screen every 3 minutes
                logger.info("\t%.2f\tseconds per loop\tsleeping for %d seconds", round(self.time_elapsed, 2), int(remaining_time/1+120))
                if not (self.ds.partial_update and not self.flip_to_dark):
                    sleep(max(2+remaining_time+120, 0))
                else:
                    # if we do partial updates and darkmode, you get a worrisome zebra stripe artifact on the EPD
                    # Create new time image, push to display, full update after 2 partials
                    partial_update_count = 0
                    while partial_update_count < 3:
                        date = dt.now()
                        sec_left = 62 - int(date.strftime("%S"))

                        if partial_update_count < 2:
                            logger.info("\t%s sleep, partial_update", round(sec_left, 2))
                            sleep(sec_left)
                        else:
                            logger.info("\t%.2f\tseconds per loop\tsleeping for %d seconds", round(self.time_elapsed, 2), int(remaining_time/1+120))
                            sleep(sec_left-self.time_elapsed)

                        if sec_left > 5 and partial_update_count < 2:
                            date = dt.now()
                            time_str = date.strftime("%-H:%M") if self.ds.twenty_four_hour_clock else date.strftime("%-I:%M") + date.strftime("%p").lower()
                            logger.info("\ttime_str:%s", time_str)
                            self.image_obj.draw_date_time_temp(self.weather_info, time_str)
                            if not self.local_run:
                                self.epd.display_Fast(self.epd.getbuffer(self.image_obj.get_image_obj()))
                            else:
                                self.save_local_file()
                        partial_update_count += 1
            elif c_hour >= 23 or c_hour < 2:
                # 11:00pm - 1:59am update screen every 5ish minutes
                logger.info("\t%.2f\tseconds per loop\tsleeping for %d seconds", round(self.time_elapsed, 2), int(remaining_time+240))
                sleep(max(2+remaining_time+240, 0))

            # Increment counter for Weather requests
            self.weather_refresh_loop_count = 0 if self.weather_refresh_loop_count == self.loops_until_weather_refresh else self.weather_refresh_loop_count + 1

    def build_image(self, time_str: Optional[str] = None) -> None:
        """
        This function builds the image for the ePaper display by drawing Spotify information, weather, date/time, and borders.
        It handles the information for two Spotify users or album art display and dark mode.

        Args:
            time_str (Optional[str]): The time string to be displayed. If not provided, the current time is used.
        """
        self.set_weather_and_sunset_info()
        time_str = self.get_time_str(time_str)
        self.image_obj.draw_date_time_temp(self.weather_info, time_str)
        self.image_obj.draw_border_lines()
        self.handle_spotify_user_1()
        self.handle_spotify_user_2_or_album_art_display()
        self.handle_dark_mode()

    def set_weather_and_sunset_info(self) -> None:
        """
        This function sets self.weather_info and self.sunset_info 
        If the information is not already available, it calls the respective functions to set them.
        """
        if not self.weather_info:
            self.set_weather()
        if not self.sunset_info:
            self.set_sunset_info()

    def get_time_str(self, time_str: Optional[str] = None) -> str:
        """
        This function returns a time string. If no time string is provided, it generates one based on the current time.

        Args:
            time_str (Optional[str]): The time string to be returned. If not provided, the current time is used.

        Returns:
            str: The time string.
        """
        if not time_str:
            date = dt.now()
            time_str = date.strftime("%-H:%M") if self.ds.twenty_four_hour_clock else date.strftime("%-I:%M") + date.strftime("%p").lower()
        return time_str

    def handle_spotify_user_1(self) -> None:
        """
        This function handles the information for Spotify User 1. 
        It retrieves the Spotify information for User 1 and draws the track info on the image.
        """
        self.old_album_name1 = self.album_name_1
        self.track_1, self.artist_1, self.time_since_1, self.ctx_type_1, self.ctx_title_1, self.track_image_link, self.album_name_1 = self.spotify_user_1.get_spotipy_info()
        x_spot_info = 5 if (self.ds.single_user and self.ds.album_art_right_side) or not self.ds.single_user else 207
        y_spot_info = 26
        self.draw_track_info(self.track_1, self.artist_1, self.ctx_type_1, self.ctx_title_1, x_spot_info, y_spot_info, self.spotify_user_1, self.time_since_1)

    def handle_spotify_user_2_or_album_art_display(self) -> None:
        """
        This function handles the information for Spotify User 2 or album art display. 
        If there is a single user, it calls the function to handle album art display. 
        Otherwise, it retrieves the Spotify information for User 2 and draws the track info on the image.

        Args:
            time_str (str): The time string to be displayed.
        """
        if not self.ds.single_user:
            track_2, artist_2, time_since_2, ctx_type_2, ctx_title_2, _, _ = self.spotify_user_2.get_spotipy_info()
            self.draw_track_info(track_2, artist_2, ctx_type_2, ctx_title_2, 207, 26, self.spotify_user_2, time_since_2)
        else:
            self.handle_album_art_display()

    def handle_album_art_display(self) -> None:
        """
        This function handles the album art display. 
        It determines the positions for the album and context based on the album art side. 
        If detailed weather forecast is enabled, it handles that. 
        Otherwise, it draws the album context. 
        Finally, it handles the album art.

        Args:
            time_str (str): The time string to be displayed.
        """
        album_pos = (201, 0) if self.ds.album_art_right_side else (0, 0)
        context_pos = (227, 204) if self.ds.album_art_right_side else (25, 204)
        if self.ds.detailed_weather_forecast:
            self.handle_detailed_weather_forecast(context_pos)
        else:
            self.image_obj.draw_spot_context("album", self.album_name_1, context_pos[0], context_pos[1])
        self.handle_album_art(album_pos)

    def handle_detailed_weather_forecast(self, context_pos: Tuple[int, int]) -> None:
        """
        This function handles the detailed weather forecast. 
        It determines whether to draw the detailed weather based on the time since the last song was played. 
        If detailed weather is to be drawn, it sets the weather mode, retrieves the four hour forecast if not already available, 
        and draws the detailed weather information. 
        Otherwise, it draws the album context.

        Args:
            context_pos (Tuple[int, int]): The position to draw the album context if detailed weather is not to be drawn.
        """
        self.draw_detailed_weather = (
            "is listening to" in self.time_since_1 and self.ds.minutes_idle_until_detailed_weather == 0
            or "minute" in self.time_since_1 and self.ds.minutes_idle_until_detailed_weather <= int(re.search(r'\d+', self.time_since_1).group())
            or "hour" in self.time_since_1 and self.ds.minutes_idle_until_detailed_weather <= int(re.search(r'\d+', self.time_since_1).group()) * 60
            or "day" in self.time_since_1 and self.ds.minutes_idle_until_detailed_weather <= int(re.search(r'\d+', self.time_since_1).group()) * 1440
        )
        self.image_obj.set_weather_mode(self.draw_detailed_weather)
        if self.draw_detailed_weather:
            self.set_four_hour_forecast()
            self.image_obj.draw_detailed_weather_border()
            self.image_obj.detailed_weather_album_name(self.album_name_1)
            self.image_obj.draw_detailed_weather_information(self.four_hour_forecast)
        else:
            self.image_obj.draw_spot_context("album", self.album_name_1, context_pos[0], context_pos[1])

    def handle_album_art(self, album_pos: Tuple[int, int]) -> None:
        """
        This function handles the album art. 
        It determines whether to get new album art based on whether the album name has changed or new album art is needed. 
        If new album art is needed and a track image link is available, it retrieves the album art. 
        It then determines the image file name based on whether a track image link is available. 
        If no track image link is available, it logs a warning. 
        It then draws the album image, date/time/temp, and border lines.

        Args:
            time_str (str): The time string to be displayed.
            album_pos (Tuple[int, int]): The position to draw the album image.
        """
        self.get_new_album_art = self.old_album_name1 != self.album_name_1 or self.get_new_album_art
        got_new_album_art = False
        if self.get_new_album_art and self.track_image_link:
            got_new_album_art = self.misc.get_album_art(self.track_image_link)
            if got_new_album_art:
                self.get_new_album_art = False
        image_file_name = "NA.png" if not self.track_image_link else None
        if not self.track_image_link:
            logger.warning("No album art found, drawing NA.png")
        self.image_obj.draw_album_image(self.flip_to_dark, image_file_name=image_file_name, pos=album_pos, convert_image=got_new_album_art)

    def handle_dark_mode(self) -> None:
        """
        This function handles the dark mode of the display. 
        If flip_to_dark is True, it calls the function to flip the display to dark mode.
        """
        if self.flip_to_dark:
            self.image_obj.dark_mode_flip()

    def draw_track_info(self, track: str, artist: str, ctx_type: str, ctx_title: str, x: int, y: int, spotify_user: SpotifyUser, time_since: str) -> None:
        """
        Draws the track information on the ePaper display.

        Parameters:
        - track (str): The name of the track.
        - artist (str): The name of the artist.
        - ctx_type (str): The context type of the track (e.g., album, playlist).
        - ctx_title (str): The title of the context.
        - x (int): The x-coordinate of the starting position.
        - y (int): The y-coordinate of the starting position.
        - spotify_user (User): The Spotify user object.
        - time_since (str): The time since the track was played.
        """
        ctx_type_is_album = ctx_type == "album"
        track_line_count, track_text_size = self.image_obj.draw_track_text(track, x, y)
        y = 210 if ctx_type_is_album else 190
        self.image_obj.draw_artist_text(artist, track_line_count, track_text_size, x, y)
        if not ctx_type_is_album:
            self.image_obj.draw_spot_context(ctx_type, ctx_title, x + 20, 204)

        name_width, name_height = self.image_obj.draw_name(spotify_user.name, x + 3, 0)
        self.image_obj.draw_user_time_ago(time_since, x + 13 + name_width, name_height // 2)

    def get_time_from_date_time(self) -> Tuple[int, str]:
        """
        Return time information from datetime including seconds, time, date, and the current_minute of update.

        Returns:
            sec_left (int): used to know how long we should sleep for before next update on the current_minute
            time_str (str): time text to be displayed
        """
        date = dt.now() + timedelta(seconds=self.time_elapsed)
        am_pm = date.strftime("%p")
        hour = int(date.strftime("%-H"))
        new_min = int(date.strftime("%M")[-1])

        # Here we make some considerations so the screen isn't updated too frequently
        # We air on the side of caution, and would rather add an additional current_minute than shrink by a current_minute
        if self.old_time and (5 < hour < 24):
            # 6:00am - 11:59pm update screen every 3 mins
            while int(abs(self.old_time - new_min)) < 3:
                date = dt.now() + timedelta(seconds=self.time_elapsed)
                new_min = int(date.strftime("%M")[-1])
                sleep(0.5)
        # 12:00am - 1:59am update screen every 5 mins at least
        elif self.old_time and hour < 2:
            while int(abs(self.old_time - new_min)) < 5:
                date = dt.now() + timedelta(seconds=self.time_elapsed)
                new_min = int(date.strftime("%M")[-1])
                sleep(0.5)
        # 2:00am - 5:59am check time every 15ish minutes, granularity here is not paramount
        sec_left = 60 - int(date.strftime("%S"))

        time_str = date.strftime("%-H:%M") if self.ds.twenty_four_hour_clock else date.strftime("%-I:%M") + am_pm.lower()
        return sec_left, time_str

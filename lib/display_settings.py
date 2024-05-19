import json

from lib.clock_logging import logger

class DisplaySettings:
    """
    The DisplaySettings class is responsible for loading display settings 
    from config/display_settings.json + a few validation checks
    """
    def __init__(self):
        with open("config/display_settings.json", encoding="utf-8") as f:
            settings = json.load(f)
            # main settings
            self.load_main_settings(settings["main_settings"])
            # single_user_settings
            self.load_single_user_settings(settings["single_user_settings"])
            # clock names
            self.load_clock_names(settings["clock_names"])
            # weather_settings
            self.load_weather_settings(settings["weather_settings"])

    def load_main_settings(self, main_settings: dict) -> None:
        """
        Load the main settings from the provided dictionary.

        Parameters:
        main_settings (dict): A dictionary containing the main settings.

        Raises:
        ValueError: If partial updates are enabled in 4 Gray Scale mode.
        """
        # switch to Dark Mode mode 30 minutes after sunset from current location
        self.sunset_flip = main_settings["sunset_flip"]
        self.always_dark_mode = main_settings["always_dark_mode"]
        # am/pm or 24 hour clock
        self.twenty_four_hour_clock = main_settings["twenty_four_hour_clock"]
        self.partial_update = main_settings["partial_update"]
        self.time_on_right = main_settings["time_on_right"]
        # it is not recommended to set sleep_epd to False as it might damage the display
        self.sleep_epd = main_settings["sleep_epd"]
        self.four_gray_scale = main_settings["four_gray_scale"]
        # Use WaveShare's 4in2epd.py or 4in2epdv2.py
        self.use_epd_lib_V2 = main_settings["use_epd_libV2"]

        if self.partial_update and self.four_gray_scale:
            raise ValueError("Partial updates are not supported in 4 Gray Scale, you must choose one or another")

        if self.sunset_flip and self.always_dark_mode:
            logger.warning("You have both sunset_flip and always_dark_mode enabled, always_dark_mode supersedes sunset_flip")

    def load_single_user_settings(self, single_user_settings: dict) -> None:
        """
        Load the single user settings from the provided dictionary.

        Parameters:
        single_user_settings (dict): A dictionary containing the single user settings.
        """
        # show two Spotify users or one Spotify user + AlbumArt or Weather Info
        self.single_user = single_user_settings["enable_single_user"]
        # if single_user is enabled, decide which side the album art should go on
        self.album_art_right_side = single_user_settings["album_art_right_side"]

    def load_clock_names(self, clock_names: dict) -> None:
        """
        Load the clock names from the provided dictionary.

        Parameters:
        clock_names (dict): A dictionary containing the clock names.
        """
        self.name_1 = clock_names["name_1"]
        self.name_2 = clock_names["name_2"]

    def load_weather_settings(self, weather_settings: dict) -> None:
        """
        Load the weather settings from the provided dictionary.

        Parameters:
        weather_settings (dict): A dictionary containing the weather settings.

        Raises:
        ValueError: If the zip code is not a 5 digit number.
        """
        self.zip_code = str(weather_settings["zip_code"]) if weather_settings["zip_code"] else None
        self.metric_units = weather_settings["metric_units"]
        self.detailed_weather_forecast = weather_settings["detailed_weather_forecast"]
        self.minutes_idle_until_detailed_weather = weather_settings[ "minutes_idle_until_detailed_weather"]
        self.use_one_call_api = weather_settings["use_one_call_api"]

        if self.zip_code and (not self.zip_code.isdigit() or not len(self.zip_code) == 5):
            raise ValueError("Zip code must be a 5 digit number")

display_settings = DisplaySettings()

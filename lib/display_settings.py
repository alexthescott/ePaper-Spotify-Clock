import json
from lib.clock_logging import logger

class DisplaySettings():
    """
    The DisplaySettings class is responsible for loading display settings from config/display_settings.json 
    """
    def __init__(self):
        with open("config/display_settings.json", encoding="utf-8") as display_settings:
            display_settings = json.load(display_settings)
            # main settings
            main_settings = display_settings["main_settings"]
            clock_names = display_settings["clock_names"]
            single_user_settings = display_settings["single_user_settings"]
            self.sunset_flip = main_settings["sunset_flip"]
            self.always_dark_mode = main_settings["always_dark_mode"]
            self.twenty_four_hour_clock = main_settings["twenty_four_hour_clock"]
            self.partial_update = main_settings["partial_update"]
            self.time_on_right = main_settings["time_on_right"]
            self.sleep_epd = main_settings["sleep_epd"] # it is not recommended to set sleep_epd to False as it might damage the display
            self.four_gray_scale = main_settings["four_gray_scale"]
            self.sunset_flip = main_settings["sunset_flip"]
            self.use_epd_lib_V2 = main_settings["use_epd_libV2"]
            # single_user_settings
            self.single_user = single_user_settings["enable_single_user"]
            self.album_art_right_side = single_user_settings["album_art_right_side"]
            self.name_1 = clock_names["name_1"]
            self.name_2 = clock_names["name_2"]
            # weather_settings
            self.weather_settings = display_settings["weather_settings"]
            self.zip_code = str(self.weather_settings["zip_code"]) if self.weather_settings["zip_code"] else None
            self.metric_units = self.weather_settings["metric_units"]
            self.hide_other_weather = self.weather_settings["hide_other_weather"]
            self.detailed_weather_forecast = self.weather_settings["detailed_weather_forecast"]

            if self.zip_code and (not self.zip_code.isdigit() or not len(self.zip_code) == 5):
                raise ValueError("Zip code must be a 5 digit number")

            if self.partial_update and self.four_gray_scale:
                raise ValueError("Partial updates are not supported in 4 Gray Scale, you must choose one or another")
            
            if self.sunset_flip and self.always_dark_mode:
                logger.warning("You have both sunset_flip and always_dark_mode enabled, always_dark_mode supersedes sunset_flip")

display_settings = DisplaySettings()
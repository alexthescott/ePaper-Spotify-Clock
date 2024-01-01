import json
from time import time, sleep, strftime, localtime
from requests import get as get_request

class Weather():
    def __init__(self):
        self.load_display_settings()
        self.OW_KEY = "" # https://openweathermap.org/ -> create account and generate key
        self.OW_CITYID = ""  # https://openweathermap.org/find? -> find your city id
        self.OW_OTHER_CITYID = "" # if hide_other_weather is True, this can be ignored 
        self.URL_UNITS = "&units=metric" if self.METRIC_UNITS else "&units=imperial" 
        self.OW_CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather?"
        self.OW_FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast?"

    def load_display_settings(self):
        # EPD Settings imported from config/display_settings.json ---------------------------------------------------
        with open('config/display_settings.json') as display_settings:
            display_settings = json.load(display_settings)
            self.SINGLE_USER = display_settings["single_user"]               # (True -> Left side album art False -> two user mode)
            self.METRIC_UNITS = display_settings["metric_units"]             # (True -> C°, False -> F°)
            self.TWENTY_FOUR_CLOCK =   display_settings["twenty_four_hour_clock"] # (True -> 22:53, False -> 10:53pm) 
            self.PARTIAL_UPDATE = display_settings["partial_update"]         # (True -> 1/60HZ Screen_Update, False -> 1/180HZ Screen_Update)
            self.TIME_ON_RIGHT = display_settings["time_on_right"]           # (True -> time is displayed on the right, False -> time is displayed on the left)
            self.HIDE_OTHER_WEATHER = display_settings["hide_other_weather"] # (True -> weather not shown in top right, False -> weather is shown in top right)
            self.SUNSET_FLIP =  display_settings["sunset_flip"]              # (True -> dark mode 24m after main sunset, False -> Light mode 24/7)

    def get_weather_and_sunset_info(self):
        """ 
        Get Weather information and sunset time

        Parameters:
            metric_units: Bool if we want C or F

        Returns:
            (temp: Current 'feels_like' temp
            temp_max: Low temp 1.5 days in the future
            temp_min: High temp 1.5 days in the future
            other_temp: Temp to be displayed in top right of other user),
            (sunset_hour: Hour of the sunset
            sunset_minute: Minute of the sunset)

        Fun Fact:
            America is a strange country with broken proclamations
            https://en.wikipedia.org/wiki/Metric_Conversion_Act
            https://www.geographyrealm.com/the-only-metric-highway-in-the-united-states/
        """
        # get local weather
        local_weather_url_request = self.OW_CURRENT_URL + "appid=" + self.OW_KEY + "&id=" + self.OW_CITYID + self.URL_UNITS
        local_weather_response = get_request(local_weather_url_request)
        local_weather_json = local_weather_response.json()

        if local_weather_json["cod"] != "404":
            temp = round(local_weather_json['main']['feels_like'])
            temp_min, temp_max = temp, temp

            sunset_unix = int(local_weather_json['sys']['sunset']) + 1440
            sunset_hour = int(strftime('%H', localtime(sunset_unix)))
            sunset_minute = int(strftime('%-M', localtime(sunset_unix)))

        # get weather for other user on the right
        if self.HIDE_OTHER_WEATHER:
            other_temp = None
        else:
            other_weather_url = self.OW_CURRENT_URL + "appid=" + self.OW_KEY + "&id=" + self.OW_OTHER_CITYID + self.URL_UNITS
            other_weather_response = get_request(other_weather_url)
            other_weather_json = other_weather_response.json()
            if other_weather_json["cod"] != "404":
                other_temp = round(other_weather_json['main']['feels_like'])

        # Get forecasted weather from feels_like and temp_min, temp_max
        local_weather_forcast_request = self.OW_FORECAST_URL + "appid=" + self.OW_KEY + "&id=" + self.OW_CITYID + self.URL_UNITS + "&cnt=12"
        local_weather_forcast_response = get_request(local_weather_forcast_request)
        forecast_json = local_weather_forcast_response.json()
        if forecast_json["cod"] != "404":
            for i, l in enumerate(forecast_json['list']):
                temp_min = min(round(l['main']['feels_like']), round(l['main']['temp_max']), temp_min)
                temp_max = max(round(l['main']['feels_like']), round(l['main']['temp_min']), temp_max)
        return (temp, temp_max, temp_min, other_temp), (sunset_hour, sunset_minute)
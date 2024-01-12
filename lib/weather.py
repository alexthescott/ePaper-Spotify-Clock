import json
from time import time, sleep, strftime, localtime
from requests import get as get_request

from lib.clock_logging import logger

class Weather():
    def __init__(self):
        self.load_display_settings()
        self.load_credentials()
        self.url_units = "units=metric" if self.metric_units else "units=imperial" 
        self.ow_current_url = "http://api.openweathermap.org/data/2.5/weather?"
        self.ow_forecast_url = "http://api.openweathermap.org/data/2.5/forecast?"
        self.ow_geocoding_url = "http://api.openweathermap.org/geo/1.0/zip?"
        self.zipcode = self.get_zip_from_ip()  # zipcode of the current location via ip, if not manually set
        self.lat_long = self.get_lat_long()  # lat and long of the current location via zipcode
        if not self.hide_other_weather:
            if len(self.ow_alt_weather_zip) == 5 and self.ow_alt_weather_zip.isdigit():
                raise Exception("ow_alt_weather_zip pair must be a zip code")

    def load_credentials(self):
        with open('config/keys.json', 'r') as f:
            credentials = json.load(f)
            self.ow_key = credentials['ow_key']
            self.ow_alt_weather_zip = credentials['ow_alt_weather_zip']

    def get_lat_long(self, current_zip=True):
        """ Get latitude and longitude from zipcode """
        if self.zipcode is None:
            return None
        else:
            local_zip = self.zipcode if current_zip else self.ow_alt_weather_zip
            url = self.ow_geocoding_url + "zip=" + local_zip + "&appid=" + self.ow_key
            response = get_request(url)
            data = response.json()
            if 'lat' in data and 'lon' in data:
                return data['lat'], data['lon']
            else:
                return None

    def get_zip_from_ip(self):
        try:
            response = get_request('http://ip-api.com/json/')
            data = response.json()
            if 'zip' in data:
                return data['zip']
        except:
            pass

        try:
            response = get_request('https://ipinfo.io/json')
            data = response.json()
            if 'postal' in data:
                return data['postal']
        except:
            pass

        return None

    def load_display_settings(self):
        # EPD Settings imported from config/display_settings.json ---------------------------------------------------
        with open('config/display_settings.json') as display_settings:
            display_settings = json.load(display_settings)
            main_settings = display_settings["main_settings"]
            self.metric_units = main_settings["metric_units"]             # (True -> C°, False -> F°)
            self.hide_other_weather = main_settings["hide_other_weather"] # (True -> weather not shown in top right, False -> weather is shown in top right)

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
        if self.zipcode is None:
            return False, False
        
        # set url to get lat and lon to the zip code of the current location using the openweathermap api

        local_weather_url_request = f"{self.ow_current_url}lat={self.lat_long[0]}&lon={self.lat_long[1]}&{self.url_units}&appid={self.ow_key}"
        local_weather_response = get_request(local_weather_url_request)

        if local_weather_response.status_code == 200:
            local_weather_json = local_weather_response.json()
            temp = round(local_weather_json['main']['feels_like'])
            temp_min, temp_max = temp, temp

            sunset_unix = int(local_weather_json['sys']['sunset']) + 1440
            sunset_hour = int(strftime('%H', localtime(sunset_unix)))
            sunset_minute = int(strftime('%-M', localtime(sunset_unix)))

        # get weather for other user on the right
        if self.hide_other_weather:
            other_temp = None
        else:
            other_weather_url = self.ow_current_url + "appid=" + self.ow_key + "&id=" + self.ow_other_cityid + self.url_units
            other_weather_response = get_request(other_weather_url)
            other_weather_json = other_weather_response.json()
            if other_weather_json["cod"] != "404":
                other_temp = round(other_weather_json['main']['feels_like'])

        # Get forecasted weather from feels_like and temp_min, temp_max
        local_weather_forcast_request = f"{self.ow_forecast_url}lat={self.lat_long[0]}&lon={self.lat_long[1]}&{self.url_units}&cnt=12&appid={self.ow_key}"
        local_weather_forcast_response = get_request(local_weather_forcast_request)
        if local_weather_forcast_response.status_code == 200:
            forecast_json = local_weather_forcast_response.json()
            for i, l in enumerate(forecast_json['list']):
                temp_min = min(round(l['main']['feels_like']), round(l['main']['temp_max']), temp_min)
                temp_max = max(round(l['main']['feels_like']), round(l['main']['temp_min']), temp_max)
        
        # use a logger message to inform all of the variables collected above
        logger.info(f"Temp: {temp}°")
        logger.info(f"Temp Min: {temp_min}°")
        logger.info(f"Temp Max: {temp_max}°")
        logger.info(f"Sunset Hour: {sunset_hour}")
        logger.info(f"Sunset Minute: {sunset_minute}")
        return (temp, temp_max, temp_min, other_temp), (sunset_hour, sunset_minute)
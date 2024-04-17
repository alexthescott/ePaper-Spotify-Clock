import json
from time import localtime, strftime
import requests

from lib.clock_logging import logger
from lib.display_settings import display_settings

class Weather():
    """
    Initializes the Weather class.

    Loads display settings, credentials, and sets up URLs for OpenWeather API.
    Retrieves the current location's zipcode and latitude/longitude.
    Used to get the weather and sunset time for the current location and sometimes the other user's location.
    """
    def __init__(self):
        self.ds = display_settings
        self.load_credentials()
        self.url_units = "units=metric" if self.ds.metric_units else "units=imperial"
        self.ow_current_url = "http://api.openweathermap.org/data/2.5/weather?"
        self.ow_forecast_url = "http://api.openweathermap.org/data/2.5/forecast?"
        self.ow_geocoding_url = "http://api.openweathermap.org/geo/1.0/zip?"
        self.zipcode = self.get_zip_from_ip()  # zipcode of the current location via ip, if not manually set
        self.lat_long = self.get_lat_long()  # lat and long of the current location via zipcode
        if not self.ds.hide_other_weather:
            if len(self.ow_alt_weather_zip) == 5 and self.ow_alt_weather_zip.isdigit():
                raise ValueError("ow_alt_weather_zip pair must be a zip code")

    def load_credentials(self):
        """
        Get OpenWeather API Key and other settings from config/keys.json
        """
        with open('config/keys.json', 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            self.ow_key = credentials['ow_key']
            self.ow_alt_weather_zip = credentials['ow_alt_weather_zip']

    def get_zip_from_ip(self):
        """
        Get zipcode from ip address from ip-api.com then ipinfo.io if ip-api.com fails
        """
        try:
            response = requests.get('http://ip-api.com/json/', timeout=10)
            data = response.json()
            if 'zip' in data:
                return data['zip']
        except requests.exceptions.RequestException:
            logger.error("Failed to get zipcode from http://ip-api.com/json/")

        try:
            response = requests.get('https://ipinfo.io/json', timeout=10)
            data = response.json()
            if 'postal' in data:
                return data['postal']
        except requests.exceptions.RequestException:
            logger.error("Failed to get zipcode from https://ipinfo.io/json")
        
        return None

    def get_lat_long(self, current_zip: bool=True):
        """ 
        Get latitude and longitude from zipcode 
        """
        local_zip = self.zipcode if current_zip else self.ow_alt_weather_zip
        if local_zip is None:
            return None, None
        url = f"{self.ow_geocoding_url}zip={local_zip}&appid={self.ow_key}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if 'lat' in data and 'lon' in data:
                return data['lat'], data['lon']
        except requests.exceptions.RequestException:
            return None, None

    def get_sunset_info(self):
        """
        Get Sunset time from OpenWeather API
        Returns:
            (sunset_hour: Hour of the sunset
            sunset_minute: Minute of the sunset)
        """
        local_weather_url_request = f"{self.ow_current_url}lat={self.lat_long[0]}&lon={self.lat_long[1]}&{self.url_units}&appid={self.ow_key}"
        local_weather_response = requests.get(local_weather_url_request, timeout=20)

        if local_weather_response.status_code == 200:
            local_weather_json = local_weather_response.json()

            sunset_unix = int(local_weather_json['sys']['sunset']) + 1440
            sunset_hour = int(strftime('%H', localtime(sunset_unix)))
            sunset_minute = int(strftime('%-M', localtime(sunset_unix)))

        return sunset_hour, sunset_minute

    def get_current_temperature_info(self):
        """
        Get current temperature, min temperature, max temperature, and other temperature from OpenWeather API
        Returns:
            temp: Current temperature
            temp_max: Max temperature
            temp_min: Min temperature
            other_temp: Other temperature
            

        Fun Fact:
            America is a strange country with broken metric promises 
            https://en.wikipedia.org/wiki/Metric_Conversion_Act
            https://www.geographyrealm.com/the-only-metric-highway-in-the-united-states/
        """
        if self.zipcode is None:
            return False, False, False, False

        local_weather_url_request = f"{self.ow_current_url}lat={self.lat_long[0]}&lon={self.lat_long[1]}&{self.url_units}&appid={self.ow_key}"
        local_weather_response = requests.get(local_weather_url_request, timeout=20)

        if local_weather_response.status_code == 200:
            local_weather_json = local_weather_response.json()
            temp = round(local_weather_json['main']['feels_like'])
            temp_min, temp_max = temp, temp

        if self.ds.hide_other_weather:
            other_temp = None
        else:
            # Fix this lol
            other_weather_url = self.ow_current_url + "appid=" + self.ow_key + "&id=" + self.ow_other_cityid + self.url_units
            other_weather_response = requests.get(other_weather_url, timeout=10)
            other_weather_json = other_weather_response.json()
            if other_weather_json["cod"] != "404":
                other_temp = round(other_weather_json['main']['feels_like'])
            else:
                other_temp = "NA"

        local_weather_forecast_request = f"{self.ow_forecast_url}lat={self.lat_long[0]}&lon={self.lat_long[1]}&{self.url_units}&cnt=12&appid={self.ow_key}"
        local_weather_forecast_response = requests.get(local_weather_forecast_request, timeout=20)
        if local_weather_forecast_response.status_code == 200:
            forecast_json = local_weather_forecast_response.json()
            for l in forecast_json['list']:
                temp_min = min(round(l['main']['feels_like']), round(l['main']['temp_max']), temp_min)
                temp_max = max(round(l['main']['feels_like']), round(l['main']['temp_min']), temp_max)

        return temp, temp_max, temp_min, other_temp

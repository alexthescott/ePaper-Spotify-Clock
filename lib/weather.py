import os
import json
from datetime import datetime, timedelta
from time import localtime, strftime

import requests

from lib.clock_logging import logger
from lib.display_settings import display_settings

class Weather():
    """
    Initializes the Weather class.

    Loads display settings, credentials, and sets up URLs for OpenWeather API.
    Retrieves the current location's zipcode and latitude/longitude.
    Used to get the weather and sunset time for the current location
    """
    def __init__(self):
        self.ds = display_settings
        self.load_credentials()
        self.url_units = "units=metric" if self.ds.metric_units else "units=imperial"
        self.ow_current_url = "http://api.openweathermap.org/data/2.5/weather?"
        self.ow_one_call_url = "https://api.openweathermap.org/data/3.0/onecall?"
        self.ow_forecast_url = "http://api.openweathermap.org/data/2.5/forecast?"
        self.ow_geocoding_url = "http://api.openweathermap.org/geo/1.0/zip?"
        self.zipcode = self.get_zip_from_ip() if not self.ds.zip_code else self.ds.zip_code  # zipcode of the current location via ip, if not manually set
        self.lat_long = self.get_lat_long()  # lat and long of the current location via zipcode
        self.local_weather_json = None
        self.local_weather_forecast_json = None
        self.one_call_json = None

    def load_credentials(self):
        """
        Get OpenWeather API Key from config/keys.json
        """
        with open('config/keys.json', 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            self.ow_key = credentials['ow_key']

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

    def get_lat_long(self):
        """ 
        Get latitude and longitude from zipcode 
        """
        local_zip = self.zipcode
        if local_zip is None:
            return None, None
        url = f"{self.ow_geocoding_url}zip={local_zip}&appid={self.ow_key}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if 'lat' in data and 'lon' in data:
                return data['lat'], data['lon']
        except requests.exceptions.RequestException as e:
            logger.error("Failed to get lat/long from %s: %s", self.ow_geocoding_url, e)
        return None, None

    def set_one_call_json(self):
        """
        Sets the one call JSON from the OpenWeather API.
        """
        file_path = 'cache/one_call_response.json'
        one_call_json_is_cached = os.path.exists(file_path)
        if one_call_json_is_cached:
            creation_time = os.path.getctime(file_path)
            creation_time = datetime.fromtimestamp(creation_time)
            # If the file was created less than 10 minutes ago
            if datetime.now() - creation_time < timedelta(minutes=10):
                with open(file_path, 'r', encoding='utf-8') as f:
                    potential_one_call_json = json.load(f)
                # Check if the lat and lon in the JSON match self.lat_lon
                if potential_one_call_json.get('lat') == self.lat_long[0] and \
                   potential_one_call_json.get('lon') == self.lat_long[1] and \
                   potential_one_call_json.get('units') == ("metric" if self.ds.metric_units else "imperial"):
                        self.one_call_json = potential_one_call_json
                        logger.info("Using one_call_response.json, created at %s", creation_time.strftime("%I:%M:%S%p %m/%d/%y"))
                        return True

        # If the file doesn't exist or was created more than 10 minutes ago, try a request call
        one_call_url_request = f"{self.ow_one_call_url}lat={self.lat_long[0]}&lon={self.lat_long[1]}&{self.url_units}&appid={self.ow_key}"
        try:
            one_call_response = requests.get(one_call_url_request, timeout=20)
        except requests.exceptions.ConnectionError as e:
            logger.error("Failed to establish a new connection: %s", e)
            # Check/Load JSON data from if one_call_response.json exists
            if one_call_json_is_cached:
                creation_time = os.path.getctime('cache/one_call_response.json')
                creation_time = datetime.fromtimestamp(creation_time)
                logger.info("Trying to use one_call_response.json, created at %s", creation_time.strftime("%I:%M:%S%p %m/%d/%y"))
                with open('cache/one_call_response.json', 'r', encoding='utf-8') as f:
                    self.one_call_json = json.load(f)
                return True
            return False

        if one_call_response.status_code == 200:
            self.one_call_json = one_call_response.json()
            self.one_call_json['units'] = "metric" if self.ds.metric_units else "imperial"
            logger.info("One Call API response: %s", one_call_response.status_code)
            # Write the JSON response to a file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.one_call_json, f, indent=2)
            return True
        else:
            logger.error("One Call API response: %s", one_call_response.json())
            return False

    def set_local_weather_json(self):
        """
        Sets the current local weather JSON from the OpenWeather API.
        """
        local_weather_url_request = f"{self.ow_current_url}lat={self.lat_long[0]}&lon={self.lat_long[1]}&{self.url_units}&appid={self.ow_key}"
        try:
            local_weather_response = requests.get(local_weather_url_request, timeout=20)
        except requests.exceptions.ConnectionError as e:
            logger.error("Failed to establish a new connection: %s", e)
            return False

        if local_weather_response.status_code == 200:
            self.local_weather_json = local_weather_response.json()
            logger.info("Current Local Weather API response: %s", local_weather_response.status_code)
            return True
        logger.error("Current Local Weather API response: %s", local_weather_response.json())
        return False
    
    def set_local_weather_forecast_json(self):
        """
        Sets the local weather forecast JSON from the OpenWeather API.
        """
        local_weather_forecast_request = f"{self.ow_forecast_url}lat={self.lat_long[0]}&lon={self.lat_long[1]}&{self.url_units}&appid={self.ow_key}"
        try:
            local_weather_forecast_response = requests.get(local_weather_forecast_request, timeout=20)
        except requests.exceptions.ConnectionError as e:
            logger.error("Failed to establish a new connection: %s", e)
            return False

        if local_weather_forecast_response.status_code == 200:
            self.local_weather_forecast_json = local_weather_forecast_response.json()
            logger.info("Local Weather Forecast API response: %s", local_weather_forecast_response.status_code)
            return True
        logger.error("Local Weather Forecast API response: %s", local_weather_forecast_response.json())
        return False

    def get_sunset_info(self):
        """
        Get Sunset time from OpenWeather API
        Returns:
            (sunset_hour: Hour of the sunset
            sunset_minute: Minute of the sunset)
        """
        if not self.local_weather_json:
            if not self.set_local_weather_json():
                return None, None

        sunset_unix = int(self.local_weather_json['sys']['sunset']) + 1440
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
            other_temp: Other temperature (will be removed in future updates)
            
        Fun Fact:
            America is a strange country with broken metric promises 
            https://en.wikipedia.org/wiki/Metric_Conversion_Act
            https://www.geographyrealm.com/the-only-metric-highway-in-the-united-states/
        """
        if self.zipcode is None or self.lat_long[0] is None or self.lat_long[1] is None:
            return "NA", "NA", "NA", "NA"
        
        if not self.set_local_weather_json():
            if not self.local_weather_json:
                return "NA", "NA", "NA", "NA"
        temp = round(self.local_weather_json['main']['feels_like'])
        temp_min, temp_max = temp, temp

        other_temp = None

        if not self.set_local_weather_forecast_json():
            if not self.local_weather_forecast_json:
                return temp, "NA", "NA", other_temp
        for l in self.local_weather_forecast_json['list']:
            temp_min = min(round(l['main']['feels_like']), round(l['main']['temp_max']), temp_min)
            temp_max = max(round(l['main']['feels_like']), round(l['main']['temp_min']), temp_max)
        return temp, temp_max, temp_min, other_temp

    def get_four_hour_forecast(self):
        """
        Get the four hour forecast from OpenWeather API
        Returns:
            forecast: List of four hour forecast
        """
        if self.ds.use_one_call_api:
            if not self.set_one_call_json():
                if not self.one_call_json:
                    return None
            # get the next 4 hours of forecast excluding the current hour
            forecasts = [self.one_call_json["hourly"][i] for i in range(7) if i % 2 == 0]
            four_day_forecast = {}
            for forecast in forecasts:
                timestamp = forecast['dt']
                dt_object = datetime.fromtimestamp(timestamp)

                # Convert and format to local timezone
                local_dt_object = dt_object.astimezone()
                formatted_time = local_dt_object.strftime("%-I%p").lower()
                
                four_day_forecast[formatted_time] = {"temp":round(forecast['feels_like']), "desc_icon_id":forecast['weather'][0]['icon']}
            return four_day_forecast
        # if we chose not to use (paid+free) one call api
        if not self.set_local_weather_forecast_json():
            if not self.local_weather_forecast_json:
                return None
        forecasts = self.local_weather_forecast_json['list'][:4]
        four_day_forecast = {}
        for l in forecasts:
            hour_forecast = datetime.fromtimestamp(l['dt']).strftime('%I%p').lstrip('0')
            four_day_forecast[hour_forecast] = {"temp":round(l['main']['feels_like']), "desc_icon_id":l['weather'][0]['icon']}
        return four_day_forecast

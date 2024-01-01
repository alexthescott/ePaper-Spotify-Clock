import json
import pdb
from time import time, sleep, strftime, localtime
from datetime import timedelta, datetime as dt

from lib.draw import Draw
from lib.weather import Weather

if __name__ == "__main__":
    # CREATE BLANK IMAGE
    image_obj = Draw()
    weather = Weather()
    image_obj.draw_border_lines()
    
    weather_info, sunset_info = weather.get_weather_and_sunset_info()
    image_obj.draw_date_time_temp(weather_info)

    import pdb; pdb.set_trace()
    image_obj.save_png("{}".format(dt.now().strftime('%H:%M:%S')));image_obj.save_png("now")
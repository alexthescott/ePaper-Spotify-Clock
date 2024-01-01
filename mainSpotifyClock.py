import json
import pdb
from time import time, sleep, strftime, localtime
from datetime import timedelta, datetime as dt

from lib.draw import Draw

if __name__ == "__main__":
    # CREATE BLANK IMAGE
    image_obj = Draw()
    image_obj.draw_border_lines()

    # replace temp_tuple with get_weather call eventually... 
    temp_tuple = (60, 63, 55, 75)
    image_obj.draw_date_time_temp(temp_tuple)

    import pdb; pdb.set_trace()
    image_obj.save_png("{}".format(dt.now().strftime('%H:%M:%S')));image_obj.save_png("now")
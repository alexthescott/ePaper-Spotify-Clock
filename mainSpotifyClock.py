import json
import pdb
from time import time, sleep, strftime, localtime
from datetime import timedelta, datetime as dt

from lib.draw import Draw
from lib.weather import Weather
from lib.spotify_user import SpotifyUser

with open('config/display_settings.json') as display_settings:
    display_settings = json.load(display_settings)
    SINGLE_USER = display_settings["single_user"]

r_ctx_type, r_ctx_title = "", ""

if __name__ == "__main__":
    # CREATE BLANK IMAGE
    image_obj = Draw()
    weather = Weather()
    image_obj.draw_border_lines()
    
    weather_info, sunset_info = weather.get_weather_and_sunset_info()
    image_obj.draw_date_time_temp(weather_info)

    if not SINGLE_USER:
        spotify_user = SpotifyUser()
    else:
        r_name = "Alex"
        spotify_user = SpotifyUser(single_user=True)
        r_track, r_artist, r_time_since, temp_ctx_type, temp_ctx_name, track_image_link, album_name = spotify_user.get_spotipy_info()
        r_ctx_type = temp_ctx_type if temp_ctx_type != "" else r_ctx_type
        r_ctx_title = temp_ctx_name if temp_ctx_name != "" else r_ctx_title
        
    # RIGHT USER TRACK TITLES CONTEXT ----------------------------------------------------------------
    track_line_count, track_text_size = image_obj.draw_track_text(r_track, 207, 26)
    image_obj.draw_artist_text(r_artist, track_line_count, track_text_size, 207, 26)
    image_obj.draw_spot_context(r_ctx_type, r_ctx_title, 227, 204)

    r_name_width, r_name_height = image_obj.draw_name(r_name, 210, 0)
    image_obj.draw_user_time_ago(r_time_since, 220 + r_name_width, r_name_height // 2)
    import pdb; pdb.set_trace()
    image_obj.save_png("{}".format(dt.now().strftime('%H:%M:%S')));image_obj.save_png("now")
import json
import pdb
from time import time, sleep, strftime, localtime
from datetime import timedelta, datetime as dt
from PIL import Image, ImageFont, ImageDraw, ImageMath

from lib.draw import Draw
from lib.weather import Weather
from lib.spotify_user import SpotifyUser
from lib.misc import save_image_from_URL, resize_image

with open('config/display_settings.json') as display_settings:
    display_settings = json.load(display_settings)
    SINGLE_USER = display_settings["single_user"]
    SUNSET_FLIP = display_settings["sunset_flip"]

r_ctx_type, r_ctx_title = "", ""

if __name__ == "__main__":
    # CREATE BLANK IMAGE
    image_obj = Draw()
    weather = Weather()
    image_obj.draw_border_lines()
    
    weather_info, sunset_info = weather.get_weather_and_sunset_info()
    image_obj.draw_date_time_temp(weather_info)

    # Should we go into darkmode?
    date = dt.now()
    c_hour = int(date.strftime("%-H"))
    c_minute = int(date.strftime("%-M"))
    sun_h, sun_m = sunset_info
    flip_to_dark = SUNSET_FLIP and ((sun_h < c_hour or c_hour < 2) or (sun_h == c_hour and sun_m <= c_minute))

    if not SINGLE_USER:
        spotify_user = SpotifyUser()
    else:
        r_name = "Alex"
        spotify_user = SpotifyUser(single_user=True)
        r_track, r_artist, r_time_since, temp_ctx_type, temp_ctx_name, track_image_link, album_name = spotify_user.get_spotipy_info()
        
        album_image_name = "AlbumImage.PNG"
        new_image_name = album_image_name.split('.')[0] + "_resize.PNG"
        save_image_from_URL(track_image_link, album_image_name)
        resize_image(album_image_name)
        image_obj.draw_album_image(new_image_name, flip_to_dark)
        image_obj.draw_spot_context("album", album_name, 25, 204)
        
        r_ctx_type = temp_ctx_type if temp_ctx_type != "" else r_ctx_type
        r_ctx_title = temp_ctx_name if temp_ctx_name != "" else r_ctx_title
        
    # RIGHT USER TRACK TITLES CONTEXT ----------------------------------------------------------------
    track_line_count, track_text_size = image_obj.draw_track_text(r_track, 207, 26)
    image_obj.draw_artist_text(r_artist, track_line_count, track_text_size, 207, 26)
    image_obj.draw_spot_context(r_ctx_type, r_ctx_title, 227, 204)

    r_name_width, r_name_height = image_obj.draw_name(r_name, 210, 0)
    image_obj.draw_user_time_ago(r_time_since, 220 + r_name_width, r_name_height // 2)

    # Darkmode ~25 minutes after the sunsets. Determined by the bool sunset_flip
    if flip_to_dark:
        image_obj.dark_mode_flip()

    import pdb; pdb.set_trace()
    image_obj.save_png("{}".format(dt.now().strftime('%H:%M:%S')));image_obj.save_png("now")
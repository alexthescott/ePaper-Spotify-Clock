import json
import pdb
from time import time, sleep, strftime, localtime
from datetime import timedelta, datetime as dt
from PIL import Image, ImageFont, ImageDraw, ImageMath

from lib.draw import Draw
from lib.weather import Weather
from lib.spotify_user import SpotifyUser
from lib.misc import Misc

with open('config/display_settings.json') as display_settings:
    display_settings = json.load(display_settings)
    SINGLE_USER = display_settings["single_user"]
    SUNSET_FLIP = display_settings["sunset_flip"]

name_1 = "Alex"
ctx_type_1, ctx_title_1 = "", ""

name_2 = "Emma"
ctx_type_2, ctx_title_2 = "", ""

if __name__ == "__main__":
    # Initialize Libs/Users
    image_obj = Draw()
    weather = Weather()
    misc = Misc()
    spotify_user_1 = SpotifyUser("Alex", single_user=SINGLE_USER)
    if not SINGLE_USER:
        spotify_user_2 = SpotifyUser("Emma", main=False)

    # Get current weather + Should we go into dark mode?
    weather_info, sunset_info = weather.get_weather_and_sunset_info()
    flip_to_dark = misc.has_sun_set(sunset_info, SUNSET_FLIP)

    # Draw collected info
    image_obj.draw_date_time_temp(weather_info)
    image_obj.draw_border_lines()

    # --- Spotify User 1 ---
    track_1, artist_1, time_since_1, tmp_ctx_type_1, tmp_ctn_name_1, track_image_link, album_name_1 = spotify_user_1.get_spotipy_info()
    track_line_count, track_text_size = image_obj.draw_track_text(track_1, 207, 26)
    image_obj.draw_artist_text(artist_1, track_line_count, track_text_size, 207, 26)

    ctx_type_1 = tmp_ctx_type_1 if tmp_ctx_type_1 != "" else ctx_type_1
    ctx_title_1 = tmp_ctn_name_1 if tmp_ctn_name_1 != "" else ctx_title_1
    image_obj.draw_spot_context(ctx_type_1, ctx_title_1, 227, 204)

    name_width_1, name_height_1 = image_obj.draw_name(name_1, 210, 0)
    image_obj.draw_user_time_ago(time_since_1, 220 + name_width_1, name_height_1 // 2)

    if not SINGLE_USER:
       # --- Spotify User 2 ---
        track_2, artist_2, time_since_2, tmp_ctx_type_2, tmp_ctn_name_2, track_image_link, album_name_2 = spotify_user_2.get_spotipy_info()
        track_line_count, track_text_size = image_obj.draw_track_text(track_1, 5, 26)
        image_obj.draw_artist_text(artist_2, track_line_count, track_text_size, 5, 26)

        ctx_type_2 = tmp_ctx_type_2 if tmp_ctx_type_2 != "" else ctx_type_2
        ctx_title_2 = tmp_ctn_name_2 if tmp_ctn_name_2 != "" else ctx_title_2
        image_obj.draw_spot_context(ctx_type_2, ctx_title_2, 25, 204)

        name_width_2, name_height_2 = image_obj.draw_name(name_2, 8, 0)
        image_obj.draw_user_time_ago(time_since_1, 18 + name_width_2, name_height_2 // 2)
    else:
        misc.get_album_art(track_image_link)
        image_obj.draw_album_image(flip_to_dark)
        image_obj.draw_spot_context("album", album_name_1, 25, 204)

    # Darkmode ~25 minutes after the sunsets. Determined by the bool sunset_flip
    if flip_to_dark:
        image_obj.dark_mode_flip()

    import pdb; pdb.set_trace()
    image_obj.save_png("{}".format(dt.now().strftime('%H:%M:%S')));image_obj.save_png("now")
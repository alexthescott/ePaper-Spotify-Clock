#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
mainSpotifyEPD.py -> Alex Scott 6/2020
single_user mode -> Ivan Chacon 12/2020

Made for the Waveshare 4.2inch e-Paper Module
https://www.waveshare.com/wiki/4.2inch_e-Paper_Module

This program finds the last thing two people listened to on Spotify, and
displays the track title, artist name, and context.

In addition, this program uses the OpenWeatherMap api to retrieve and
display the current 'feels-like' temperature, along with the date and time

6:00am - 11:59pm the display updates every 3 minutes
12:00pm - 2:00am the display updates every 15 minutes
2:00am - 6:00am the display does not update
This is all in an effort to ensure the display does not see long term damage

A preview of the end result can be found here:
https://raw.githubusercontent.com/alexthescott/4.2in-ePaper-Spotify-Clock/master/spotify_epaper_preview.jpg

This program is intended to be used along with a bash script which re-launches
the program in the event of a crash. That bash script can be found here:
https://github.com/alexthescott/4.2in-ePaper-Spotify-Clock/blob/master/launch_epaper.sh
"""

import spotipy
from os.path import splitext
from time import time, sleep, strftime, localtime
from datetime import timedelta, datetime as dt
from requests import get as get_request
from waveshare_epd import epd4in2
from PIL import Image, ImageDraw, ImageMath

# Local .py dependencies
import localJsonIO as ctx_io
import drawToEPD as epd_draw


def main_loop():
    """ Our main_loop enters a while loop, updating the EPD every 3 mins using spotify, weather, and dt information. """

    # Generate Spotify client_id and client_secret
    # https://developer.spotify.com/dashboard/
    spot_scope = "user-read-private, user-read-recently-played, user-read-playback-state, user-read-currently-playing"
    redirect_uri = 'http://www.google.com/'

    # if single_user is True, Left Spotify info is never shown
    l_spot_client_id = ''
    l_spot_client_secret = ''
    l_cache = '.leftauthcache'
    l_name = ''     # displayed at the top of the screen

    # Right Spotify
    r_spot_client_id = ''
    r_spot_client_secret = ''
    r_cache = '.rightauthcache'
    r_name = ''

    # EPD Settings ------------------------------------------------------------------
    single_user = False        # (True -> Left side album art, False -> ignore r user)
    metric_units = False       # (True -> C°, False -> F°)
    twenty_four_clock = False  # (True -> 10:53pm, False -> 22:53)
    partial_updates = True     # (True -> 1/60HZ Screen_Update, False -> 1/180HZ Screen_Update)
    sunset_flip = True         # (True -> darkmode 24m after main sunset, False Light mode 24/7)
    # -------------------------------------------------------------------------------

    epd = epd4in2.EPD()
    WIDTH, HEIGHT = epd.width, epd.height
    r_ctx_type, r_ctx_title, l_ctx_type, l_ctx_title = "", "", "", ""

    # count_to_5 is used to get weather every 5 minutes
    count_to_5 = 0
    time_elapsed = 15.0
    old_time, temp_tuple = None, None
    sunset_time_tuple = None

    # First loop, init EPD
    did_epd_init = False

    try:
        while True:
            # Get time variables. old_time is used to ensure even time difference intervals between updates
            sec_left, time_str, date_str, old_time = get_time_from_date_time(time_elapsed, old_time, twenty_four_clock)
            print(time_str)

            # Firstly, this is for my own edifice to know how long a loop takes for the Pi
            # Secondly, this is used to 'push' our clock forward such that our clock update is exactly on time
            start = time()

            # OPENWEATHER API CALL
            if temp_tuple is None or count_to_5 == 4:
                temp_tuple, sunset_time_tuple = get_weather(metric_units)

            # Should we go into darkmode?
            date = dt.now() + timedelta(seconds=time_elapsed)
            c_hour = int(date.strftime("%-H"))
            c_minute = int(date.strftime("%-M"))
            sun_h, sun_m = sunset_time_tuple
            flip_to_dark = sunset_flip and ((sun_h < c_hour or c_hour < 2) or (sun_h == c_hour and sun_m <= c_minute))

            # CREATE BLANK IMAGE
            image_obj = Image.new('1', (WIDTH, HEIGHT), 128)
            draw = ImageDraw.Draw(image_obj)

            # GET right user's SPOTIFY TOKEN
            print("Get right user's Spotify Token")
            r_oauth = spotipy.oauth2.SpotifyOAuth(r_spot_client_id, r_spot_client_secret, redirect_uri, scope=spot_scope, cache_path=r_cache, requests_timeout=10)
            r_token_info = r_oauth.get_cached_token()
            r_token = get_spotipy(r_oauth, r_token_info)
            if r_token:
                r_track, r_artist, r_time_since, temp_ctx_type, temp_ctx_name, track_image_link, album_name = get_spotipy_info(r_token, single_user)
                r_ctx_type = temp_ctx_type if temp_ctx_type != "" else r_ctx_type
                r_ctx_title = temp_ctx_name if temp_ctx_name != "" else r_ctx_title
            else:
                print(":( Right's access token unavailable")
                r_track, r_artist = "", ""

            # GET left user's SPOTIPY AUTH OBJECT, TOKEN
            if not single_user:
                print("Get left user's Spotify Token")
                l_oauth = spotipy.oauth2.SpotifyOAuth(l_spot_client_id, l_spot_client_secret, redirect_uri, scope=spot_scope, cache_path=l_cache, requests_timeout=10)
                l_token_info = l_oauth.get_cached_token()
                l_token = get_spotipy(l_oauth, l_token_info)
                if l_token:
                    l_track, l_artist, l_time_since, temp_ctx_type, temp_ctx_name, _, _ = get_spotipy_info(l_token, False)
                    l_ctx_type = temp_ctx_type if temp_ctx_type != "" else l_ctx_type
                    l_ctx_title = temp_ctx_name if temp_ctx_name != "" else l_ctx_title
                else:
                    print(":( Left's access token unavailable")
                    l_track, l_artist = "", ""
            else:
                album_image_name = "AlbumImage.PNG"
                new_image_name = album_image_name.split('.')[0] + "_resize.PNG"
                save_image_from_URL(track_image_link, album_image_name)
                resize_image(album_image_name)

            # If we have no context read, grab context our context.txt json file
            if (l_ctx_type == "" and l_ctx_title == "") or (r_ctx_type == "" and r_ctx_title == ""):
                try:
                    fh = open('context.txt')
                    l_ctx_type, l_ctx_title, r_ctx_type, r_ctx_title = ctx_io.read_json_ctx((l_ctx_type, l_ctx_title), (r_ctx_type, r_ctx_title))
                    fh.close()
                except:
                    print("context.txt doesn't exist")
            # Afterwords, if we have to write a new context to our context.txt json file, do so
            if (l_ctx_type != "" and l_ctx_title != "") or (r_ctx_type != "" and r_ctx_title != ""):
                ctx_io.write_json_ctx((l_ctx_type, l_ctx_title), (r_ctx_type, r_ctx_title))

            if single_user:
                # ALBUM ART COVER FOR USER ----------------------------------------------------------------
                epd_draw.draw_album_image(image_obj, new_image_name, flip_to_dark)
                epd_draw.draw_spot_context(draw, image_obj, "album", album_name, 25, 204)
            else:
                # LEFT USER TRACK TITLES CONTEXT ----------------------------------------------------------------
                track_line_count, track_text_size = epd_draw.draw_track_text(draw, l_track, 5, 26)
                epd_draw.draw_artist_text(draw, l_artist, track_line_count, track_text_size, 5, 26)
                epd_draw.draw_spot_context(draw, image_obj, l_ctx_type, l_ctx_title, 25, 204)
                # DRAW NAMES TIME SINCE ----------------------------------------------------------------
                l_name_width, l_name_height = epd_draw.draw_name(draw, l_name, 8, 0)
                epd_draw.draw_user_time_ago(draw, l_time_since, 18 + l_name_width, l_name_height // 2)

            # RIGHT USER TRACK TITLES CONTEXT ----------------------------------------------------------------
            track_line_count, track_text_size = epd_draw.draw_track_text(draw, r_track, 207, 26)
            epd_draw.draw_artist_text(draw, r_artist, track_line_count, track_text_size, 207, 26)
            epd_draw.draw_spot_context(draw, image_obj, r_ctx_type, r_ctx_title, 227, 204)

            r_name_width, r_name_height = epd_draw.draw_name(draw, r_name, 210, 0)
            epd_draw.draw_user_time_ago(draw, r_time_since, 220 + r_name_width, r_name_height // 2)

            # DRAW LINES DATE TIME TEMP ----------------------------------------------------------------
            epd_draw.draw_border_lines(draw)
            epd_draw.draw_date_time_temp(draw, time_str, date_str, temp_tuple, metric_units)

            # Get 24H clock c_hour to determine sleep duration before refresh
            date = dt.now() + timedelta(seconds=time_elapsed)
            c_hour = int(date.strftime("%-H"))
            c_minute = int(date.strftime("%-M"))

            # save instance of image
            image_obj.save("screenCapture.png")

            # HIDDEN DARK MODE
            # image_obj = ImageMath.eval('255-(a)',a=image_obj)

            # Darkmode ~25 minutes after the sunsets. Determined by the bool sunset_flip
            if flip_to_dark:
                print("After sunset dark mode")
                image_obj = ImageMath.eval('255-(a)', a=image_obj)

            # from 2:01 - 5:59am, don't init the display, return from main, and have .sh script run again in 3 mins
            if 2 <= c_hour and c_hour <= 5:
                if did_epd_init:
                    # in sleep() from epd4in2.py, epdconfig.module_exit() is never called
                    # I hope this does not create long term damage 🤞
                    print("EPD Sleep(ish) ....")
                    break
                else:
                    print("Don't Wake")
                    break
            elif not did_epd_init:
                print("EPD INIT")
                epd.init()
                epd.Clear()
                did_epd_init = True

            if did_epd_init:
                image_buffer = epd.getbuffer(image_obj)
                print("\tDrawing Image to EPD")
                epd.display(image_buffer)

            # Look @ start variable above. find out how long it takes to compute our image
            stop = time()
            time_elapsed = stop - start

            remaining_time = sec_left - time_elapsed
            remaining_time = 60 if remaining_time < 0 else remaining_time

            if 5 < c_hour and c_hour < 24:
                # 6:00am - 12:59pm update screen every 3 minutes
                print("\t", round(time_elapsed, 2), "\tseconds per loop\t", "sleeping for {} seconds".format(int(remaining_time) + 120))
                # if we do partial updates and darkmode, you get a worrisome zebra stripe artifact on the EPD
                if partial_updates and not flip_to_dark:
                    # Create new time image, push to display, full update after 2 partials
                    partial_updates = 0
                    while partial_updates < 3:
                        date = dt.now()
                        sec_left = 62 - int(date.strftime("%S"))

                        if partial_updates < 2:
                            print("\t{}s sleep, partial_update".format(round(sec_left, 2)))
                            sleep(sec_left)
                        else:
                            print("\t{}s sleep, full refresh".format(round(sec_left - time_elapsed, 2)))
                            sleep(sec_left - time_elapsed)

                        if sec_left > 5 and partial_updates < 2:
                            date = dt.now()
                            time_str = date.strftime("%-H:%M") if twenty_four_clock else date.strftime("%-I:%M") + date.strftime("%p").lower()
                            print("\ttimestr:{}".format(time_str))
                            time_image, time_width = epd_draw.create_time_text(draw, time_str, date_str, temp_tuple, metric_units)
                            epd.EPD_4IN2_PartialDisplay(5, 245, 5 + time_width, 288, epd.getbuffer(time_image))
                        partial_updates += 1
                else:
                    sleep(remaining_time + 120)
            elif c_hour < 2:
                # 12:00am - 1:59am update screen every 5ish minutes
                print("\t", round(time_elapsed, 2), "\tseconds per loop\t", "sleeping for {} seconds".format(int(remaining_time) + 240))
                sleep(remaining_time + 240)
                # maybe partial updates here too? Every 2 mins?

            # Increment counter for Weather requests
            count_to_5 = 0 if count_to_5 == 4 else count_to_5 + 1

    except Exception as e:
        with open("bugs.txt", "a+") as error_file:
            file_text = error_file.read()
            if str(e) in file_text:
                print("bug already caught")
            else:
                print("new bug caught\n" + str(e))
                error_file.write(str(e) + "\n")
        print("Retrying main_loop() in 20 seconds...")
        sleep(20)
        main_loop()


# Spotify Functions
def get_spotipy(sp_oauth, token_info):
    """ Return Spotify Token from sp_oauth if token_ifo is stale. """
    token = None
    if token_info:
        token = token_info['access_token']
    else:
        auth_url = sp_oauth.get_authorize_url()
        print(auth_url)
        response = input("Paste the above link into your browser, then paste the redirect url here: ")
        code = sp_oauth.parse_response_code(response)
        if code:
            print("Found Spotify auth code in Request URL! Trying to get valid access token...")
            token_info = sp_oauth.get_access_token(code)
            token = token_info['access_token']
    return token


def get_spotipy_info(token, single_user):
    """ Return Spotify Listening Information from Spotify AUTH Token.

        Parameters:
            token: Spotify Auth Token generated from OAuth object
        Return:
            track_name: track name to be displayed
            artist_name: artist name to be displayed
            time_passed: used to calculate time since played, or if currently playing
            context_type: used to determine context icon -> pulled from get_context_from_json()
            context_name: context name to be displayed -> pulled from get_context_from_json()
    """
    sp = spotipy.Spotify(auth=token)
    recent = sp.current_user_playing_track()
    context_type, context_name, time_passed = "", "", ""
    track_image_link, album_name = None, None  # used if single_user
    if recent is not None and recent['item'] is not None:
        # GET CURRENT CONTEXT
        context_type, context_name = get_context_from_json(recent['context'], sp)
        time_passed = " is listening to"

        # GET TRACK && ARTIST
        track_name, artists = recent['item']['name'], recent['item']['artists']
        artist_name = ""
        for i in range(len(artists)):
            artist_name += artists[i]['name'] + ", "
        artist_name = artist_name[:-2]

        # need image data as single_user
        if single_user:
            track_image_link = recent['item']['album']['images'][0]['url']
            album_name = recent['item']['album']['name']
    else:
        # GRAB OLD CONTEXT
        recent = sp.current_user_recently_played(1)
        tracks = recent["items"]
        track = tracks[0]
        track_name, artists = track['track']['name'], track['track']['artists']
        track_image_link = tracks[0]['track']['album']['images'][0]['url']
        album_name = track['track']['album']['name']
        # Concatinate artist names
        artist_name = ""
        for i in range(len(artists)):
            artist_name += track['track']['artists'][i]['name'] + ", "
        artist_name = artist_name[:-2]

        last_timestamp = track['played_at']
        str_timestamp = last_timestamp[:10] + " " + last_timestamp[11:19]
        timestamp = dt.strptime(str_timestamp, "%Y-%m-%d %H:%M:%S")
        hours_passed, minutes_passed = get_time_from_timedelta(dt.utcnow() - timestamp)
        time_passed = get_time_since_played(hours_passed, minutes_passed)
        context_type, context_name = get_context_from_json(track['context'], sp)
    return track_name, artist_name, time_passed, context_type, context_name, track_image_link, album_name


def get_context_from_json(context_json, spotipy_object):
    """ Return Spotify Context info.

        Parameters:
            context_json: json to be parsed
            spotipy_object: used to retreive name of spotify context
        Return:
            context_type: Either a playlist, artist, or album
            context_name: Context name to be displayed
    """
    context_type, context_name = "", ""
    if context_json is not None:
        context_type = context_json['type']
        context_uri = context_json['uri']
        if context_type == 'playlist':
            playlist_json = spotipy_object.playlist(context_uri)
            context_name = playlist_json['name']
        elif context_type == 'album':
            album_json = spotipy_object.album(context_uri)
            context_name = album_json['name']
        elif context_type == 'artist':
            artist_json = spotipy_object.artist(context_uri)
            context_name = artist_json['name']
    return context_type, context_name


# Time Functions
def get_time_from_date_time(time_elapsed, old_min, twenty_four_clock):
    """ Return time information from datetime including seconds, time, date, and the current_minute of update.

        Parameters:
            time_elapsed: 'jump us forward in time to anticipate compute time'
            old_min: used to ensure a proper update interval
            twenty_four_clock: Bool to determine if AM/PM or not
        Returns:
            sec_left: used to know how long we should sleep for before next update on the current_minute
            time_str: time text to be displayed
            date_str: date text to be displayed
            new_min: will become the old_min var in next call for proper interval
    """
    date = dt.now() + timedelta(seconds=time_elapsed)
    am_pm = date.strftime("%p")
    hour = int(date.strftime("%-H"))
    new_min = int(date.strftime("%M")[-1])

    # Here we make some considerations so the screen isn't updated too frequently
    # We air on the side of caution, and would rather add an additional current_minute than shrink by a current_minute
    if old_min is not None and (5 < hour and hour < 24):
        # 6:00am - 11:59pm update screen every 3 mins
        while int(abs(old_min - new_min)) < 3:
            date = dt.now() + timedelta(seconds=time_elapsed)
            new_min = int(date.strftime("%M")[-1])
            sleep(2)
    # 12:00am - 1:59am update screen every 5 mins at least
    elif old_min is not None and (hour < 2):
        while int(abs(old_min - new_min)) < 5:
            date = dt.now() + timedelta(seconds=time_elapsed)
            new_min = int(date.strftime("%M")[-1])
            sleep(2)
    # 2:00am - 5:59am check time every 15ish minutes, granularity here is not paramount
    sec_left = 60 - int(date.strftime("%S"))
    date_str, am_pm = date.strftime("%a, %b %-d"), date.strftime("%p")

    time_str = date.strftime("%-H:%M") if twenty_four_clock else date.strftime("%-I:%M") + am_pm.lower()
    return sec_left, time_str, date_str, int(new_min)


def get_time_from_timedelta(td):
    """ Determine time since last played in terms of hours and minutes from timedelta. """
    hours, minutes = td.days * 24 + td.seconds // 3600, (td.seconds % 3600) // 60
    return hours, minutes


def get_time_since_played(hours, minutes):
    """ Get str representation of time since last played.

        Parameters:
            hours: int counting hours since last played
            minutes: int counting minutes since last played
        Returns:
            "is listening to" or "# ___ ago"
    """
    if hours == 0 and minutes <= 4:
        return " is listening to"
    elif hours == 0:
        return str(minutes - (minutes % 5)) + "  minutes ago"
    elif hours == 1:
        return str(hours) + "  hour ago"
    elif hours < 24:
        return str(hours) + "  hours ago"
    elif hours < 48:
        return str(hours // 24) + "  day ago"
    else:
        return str(hours // 24) + "  days ago"


def get_weather(metric_units):
    """ Get Weather information
        Parameters:
            metric_units: Bool if we want C or F
        Returns:
            temp: Current 'feels_like' temp
            temp_max: Low temp 1.5 days in the future
            temp_min: High temp 1.5 days in the future
            other_temp: Temp to be displayed in top right of other user (another city perhaps?)

        Fun Fact:
            America is a strange country with broken proclamations
            https://en.wikipedia.org/wiki/Metric_Conversion_Act
            https://www.geographyrealm.com/the-only-metric-highway-in-the-united-states/
    """
    OW_KEY = ""  # https://openweathermap.org/ -> create account and generate key
    OW_CITYID = ""  # https://openweathermap.org/find? -> find your city id
    OW_OTHER_CITYID = ""
    URL_UNITS = "&units=metric" if metric_units else "&units=imperial" 

    # Get current weather
    OW_CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather?"
    OW_CURRENT_COMPLETE = OW_CURRENT_URL + "appid=" + OW_KEY + "&id=" + OW_CITYID + URL_UNITS
    weather_response = get_request(OW_CURRENT_COMPLETE)
    weather_json = weather_response.json()

    if weather_json["cod"] != "404":
        temp = round(weather_json['main']['feels_like'])
        temp_min, temp_max = temp, temp

        sunset_unix = int(weather_json['sys']['sunset']) + 1440
        sunset_hour = int(strftime('%H', localtime(sunset_unix)))
        sunset_minute = int(strftime('%-M', localtime(sunset_unix)))
        # print(strftime("%H:%M:%S", localtime(sunset_unix)))

    # get current weather for user on the right
    OW_CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather?"
    OW_CURRENT_COMPLETE = OW_CURRENT_URL + "appid=" + OW_KEY + "&id=" + OW_OTHER_CITYID + URL_UNITS
    weather_response = get_request(OW_CURRENT_COMPLETE)
    weather_json = weather_response.json()
    if weather_json["cod"] != "404":
        other_temp = round(weather_json['main']['feels_like'])

    # Get forecasted weather from feels_like and temp_min, temp_max
    OW_FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast?"
    OW_FORECAST_COMPLETE = OW_FORECAST_URL + "appid=" + OW_KEY + "&id=" + OW_CITYID + URL_UNITS + "&cnt=12"
    weather_response = get_request(OW_FORECAST_COMPLETE)
    forecast_json = weather_response.json()
    if forecast_json["cod"] != "404":
        for i, l in enumerate(forecast_json['list']):
            temp_min = min(round(l['main']['feels_like']), round(l['main']['temp_max']), temp_min)
            temp_max = max(round(l['main']['feels_like']), round(l['main']['temp_min']), temp_max)
    return (temp, temp_max, temp_min, other_temp), (sunset_hour, sunset_minute)

# -----------------------------------------------------------------------------
# Below is used to pull album artwork. Written by -> iuc73663.github.io
# -----------------------------------------------------------------------------
def get_album_URL(user):
    recent = user.current_user_recently_played(limit=1)
    tracks = recent["items"]
    track_image_link = tracks[0]['track']['album']['images'][0]['url']
    return track_image_link


def save_image_from_URL(track_image_link, fileName):
    img_data = get_request(track_image_link).content
    with open(fileName, 'wb') as handler:
        handler.write(img_data)


def resize_image(imageName):
    # 198 = width
    # 223 = height
    size = 199, 199
    outfile = splitext(imageName)[0] + "_resize.PNG"
    if imageName != outfile:
        try:
            im = Image.open(imageName)
            im.thumbnail(size, Image.ANTIALIAS)
            im.save(outfile, "PNG")
        except IOError:
            print ("cannot create thumbnail for '%s'" % imageName)
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    main_loop()

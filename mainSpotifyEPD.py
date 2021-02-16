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
import json
from os.path import splitext
from time import time, sleep, strftime, localtime
from datetime import timedelta, datetime as dt
from requests import get as get_request
from waveshare_epd import epd4in2
from PIL import Image, ImageFont, ImageDraw, ImageMath

# EPD Settings just for you! --------------------------------------------------------------------------------
single_user = False        # (True -> Left side album art False -> two user mode)
metric_units = False       # (True -> C°, False -> F°)
twenty_four_clock = False  # (True -> 10:53pm, False -> 22:53)
partial_updates = True     # (True -> 1/60HZ Screen_Update, False -> 1/180HZ Screen_Update)
time_on_right = True       # (True -> time is displayed on the right, False -> time is displayed on the left)
hide_other_weather = False # (True -> weather not shown in top right, False -> weather is shown in top right)
sunset_flip = True         # (True -> darkmode 24m after main sunset, False -> Light mode 24/7)
# -----------------------------------------------------------------------------------------------------------

# Generate Spotify client_id and client_secret
# https://developer.spotify.com/dashboard/
spot_scope = "user-read-private, user-read-recently-played, user-read-playback-state, user-read-currently-playing"
redirect_uri = 'http://www.google.com/'

# if single_user is True, Left Spotify info is never shown
l_spot_client_id = ''
l_spot_client_secret = ''
l_cache = '.leftauthcache'
l_name = '' # drawn at the top of the screen

# Right Spotify
r_spot_client_id = ''
r_spot_client_secret = ''
r_cache = '.rightauthcache'
r_name = '' # drawn at the top of the screen

WIDTH, HEIGHT = 400, 300

def main_loop():
    """ Our main_loop enters a while loop, updating the EPD every 3 mins using spotify, weather, and dt information. """

    epd = epd4in2.EPD()

    # count_to_5 is used to get weather every 5 minutes
    count_to_5 = 0
    time_elapsed = 15.0
    old_time, temp_tuple = None, None
    sunset_time_tuple = None
    r_ctx_type, r_ctx_title, l_ctx_type, l_ctx_title = "", "", "", ""

    # First loop, init EPD
    did_epd_init = False

    epd_draw = DrawToEPD()
    ctx_io = LocalJsonIO()

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
                temp_tuple, sunset_time_tuple = get_weather(metric_units, hide_other_weather)

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
            epd_draw.draw_date_time_temp(draw, time_str, date_str, temp_tuple, metric_units, time_on_right, hide_other_weather)

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
                print("\t", round(time_elapsed, 2),"\tseconds per loop\t", "sleeping for {} seconds".format(int(remaining_time) + 120))
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
                            time_image, time_width = epd_draw.create_time_text(draw, time_str, date_str, temp_tuple, metric_units, time_on_right, hide_other_weather)
                            if time_on_right:
                                epd.EPD_4IN2_PartialDisplay(WIDTH - 5 - time_width, 245, WIDTH - 5, 288, epd.getbuffer(time_image))
                            else:
                                epd.EPD_4IN2_PartialDisplay(5, 245, 5 + time_width, 288, epd.getbuffer(time_image))
                        partial_updates += 1
                else:
                    sleep(remaining_time + 120)
            elif c_hour < 2:
                # 12:00am - 1:59am update screen every 5ish minutes
                print("\t", round(time_elapsed, 2),"\tseconds per loop\t", "sleeping for {} seconds".format(int(remaining_time) + 240))
                sleep(remaining_time + 240)

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


def get_weather(metric_units, hide_other_weather):
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

    # get current weather for user on the right
    if not hide_other_weather:
        OW_CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather?"
        OW_CURRENT_COMPLETE = OW_CURRENT_URL + "appid=" + OW_KEY + "&id=" + OW_OTHER_CITYID + URL_UNITS
        weather_response = get_request(OW_CURRENT_COMPLETE)
        weather_json = weather_response.json()
        if weather_json["cod"] != "404":
            other_temp = round(weather_json['main']['feels_like'])
    else:
        other_temp = None

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

class DrawToEPD():
    """ DrawToEPD by Alex Scott 2021
    Companion functions for mainSpotifyEPD.py

    Functions here rely on PIL to draw to an existing draw object
    Draw context, date time temp, artist and track info, time since, and names

    Made for the Waveshare 4.2inch e-Paper Module
    https://www.waveshare.com/wiki/4.2inch_e-Paper_Module
    """
    def __init__(self):
        self.WIDTH = 400
        self.HEIGHT = 300
        # dictionaries hold pixel width for each char, given thre three font sizes
        self.sfDict = None
        self.mfDict = None
        self.lfDict = None
        self.set_dictionaries()

        # Load local resources. Fonts and Icons from /ePaperFonts and /Icons
        self.DSfnt16 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 16)
        self.DSfnt32 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 32)
        self.DSfnt64 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 64)

        self.helveti16 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 16)
        self.helveti32 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 32)
        self.helveti64 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 64)

        self.playlist_icon = Image.open('Icons/playlist.png')
        self.artist_icon = Image.open('Icons/artist.png')
        self.album_icon = Image.open('Icons/album.png')

    def set_dictionaries(self):
        # Used to get the pixel length of strings as they're built
        self.sfDict = {' ': '2', '!': '2', '"': '4', '#': '8', '$': '6', '%': '8',
        '&': '7', "'": '2', '(': '4', ')': '4', '*': '8', '+': '6', ',': '3',
        '-': '6', '.': '2', '/': '4', '0': '6', '1': '3', '2': '6', '3': '6',
        '4': '7', '5': '6', '6': '6', '7': '6', '8': '6', '9': '6', ':': '2',
        ';': '3', '<': '4', '=': '6', '>': '4', '?': '5', '@': '8', 'A': '6',
        'B': '6', 'C': '6', 'D': '6', 'E': '5', 'F': '5', 'G': '6', 'H': '6',
        'I': '2', 'J': '5', 'K': '6', 'L': '5', 'M': '6', 'N': '6', 'O': '6',
        'P': '6', 'Q': '6', 'R': '6', 'S': '5', 'T': '6', 'U': '6', 'V': '6',
        'W': '6', 'X': '6', 'Y': '6', 'Z': '5', '[': '4', '\\': '4', ']': '4',
        '^': '4', '_': '6', 'a': '6', 'b': '6', 'c': '6', 'd': '6', 'e': '6',
        'f': '5', 'g': '6', 'h': '6', 'i': '2', 'j': '4', 'k': '5', 'l': '3',
        'm': '8', 'n': '6', 'o': '6', 'p': '6', 'q': '6', 'r': '5', 's': '5',
        't': '5', 'u': '6', 'v': '6', 'w': '6', 'x': '6', 'y': '6', 'z': '6',
        '{': '5', '|': '2', '}': '5', '~': '6', '¡': '2', '¢': '7', '£': '6',
        '©': '10', '®': '10', '±': '6', '¿': '5', 'À': '6', 'Á': '6', 'Â': '6',
        'Ä': '6', 'Ç': '5', 'È': '5', 'É': '5', 'Ê': '5', 'Ë': '5', 'Ì': '3',
        'Í': '3', 'Î': '4', 'Ï': '4', 'Ñ': '6', 'Ò': '6', 'Ó': '6', 'Ô': '6',
        'Ö': '6', '×': '6', 'Ù': '6', 'Ú': '6', 'Û': '6', 'Ü': '6', 'ß': '6',
        'à': '6', 'á': '6', 'â': '6', 'ä': '6', 'è': '6', 'é': '6', 'ê': '6',
        'ë': '6', 'ì': '3', 'í': '3', 'î': '4', 'ï': '4', 'ñ': '6', 'ò': '6',
        'ó': '6', 'ô': '6', 'ö': '6', '÷': '6', 'ù': '6', 'ú': '6', 'û': '6',
        'ü': '6', '‘': '3', '’': '3', '“': '5', '”': '5', '…': '6', '€': '7',
        '™': '10', '\x00': '9'}
        self.mfDict = {' ': '4', '!': '4', '"': '8', '#': '16', '$': '12', '%': '16',
        '&': '14', "'": '4', '(': '8', ')': '8', '*': '16', '+': '12', ',': '6',
        '-': '12', '.': '4', '/': '8', '0': '12', '1': '6', '2': '12', '3': '12',
        '4': '14', '5': '12', '6': '12', '7': '12', '8': '12', '9': '12',
        ':': '4', ';': '6', '<': '8', '=': '12', '>': '8', '?': '10', '@': '16',
        'A': '12', 'B': '12', 'C': '12', 'D': '12', 'E': '10', 'F': '10',
        'G': '12', 'H': '12', 'I': '4', 'J': '10', 'K': '12', 'L': '10',
        'M': '12', 'N': '12', 'O': '12', 'P': '12', 'Q': '12', 'R': '12',
        'S': '10', 'T': '12', 'U': '12', 'V': '12', 'W': '12', 'X': '12',
        'Y': '12', 'Z': '10', '[': '8', '\\': '8', ']': '8', '^': '8', '_': '12',
        'a': '12', 'b': '12', 'c': '12', 'd': '12', 'e': '12', 'f': '10',
        'g': '12', 'h': '12', 'i': '4', 'j': '8', 'k': '10', 'l': '6', 'm': '16',
        'n': '12', 'o': '12', 'p': '12', 'q': '12', 'r': '10', 's': '10',
        't': '10', 'u': '12', 'v': '12', 'w': '12', 'x': '12', 'y': '12',
        'z': '12', '{': '10', '|': '4', '}': '10', '~': '12', '¡': '4',
        '¢': '14', '£': '12', '©': '20', '®': '20', '±': '12', '¿': '10',
        'À': '12', 'Á': '12', 'Â': '12', 'Ä': '12', 'Ç': '10', 'È': '10',
        'É': '10', 'Ê': '10', 'Ë': '10', 'Ì': '6', 'Í': '6', 'Î': '8', 'Ï': '8',
        'Ñ': '12', 'Ò': '12', 'Ó': '12', 'Ô': '12', 'Ö': '12', '×': '12',
        'Ù': '12', 'Ú': '12', 'Û': '12', 'Ü': '12', 'ß': '12', 'à': '12',
        'á': '12', 'â': '12', 'ä': '12', 'è': '12', 'é': '12', 'ê': '12',
        'ë': '12', 'ì': '6', 'í': '6', 'î': '8', 'ï': '8', 'ñ': '12', 'ò': '12',
        'ó': '12', 'ô': '12', 'ö': '12', '÷': '12', 'ù': '12', 'ú': '12',
        'û': '12', 'ü': '12', '‘': '6', '’': '6', '“': '10', '”': '10',
        '…': '12', '€': '14', '™': '20', '\x00': '18'}
        self.lfDict = {' ': '9', '!': '9', '"': '17', '#': '33', '$': '25', '%': '33',
        '&': '29', "'": '9', '(': '17', ')': '17', '*': '33', '+': '25',
        ',': '13', '-': '25', '.': '9', '/': '17', '0': '25', '1': '13',
        '2': '25', '3': '25', '4': '29', '5': '25', '6': '25', '7': '25',
        '8': '25', '9': '25', ':': '9', ';': '13', '<': '17', '=': '25',
        '>': '17', '?': '21', '@': '33', 'A': '25', 'B': '25', 'C': '25',
        'D': '25', 'E': '21', 'F': '21', 'G': '25', 'H': '25', 'I': '9',
        'J': '21', 'K': '25', 'L': '21', 'M': '25', 'N': '25', 'O': '25',
        'P': '25', 'Q': '25', 'R': '25', 'S': '21', 'T': '25', 'U': '25',
        'V': '25', 'W': '25', 'X': '25', 'Y': '25', 'Z': '21', '[': '17',
        '\\': '17', ']': '17', '^': '17', '_': '25', 'a': '25', 'b': '25',
        'c': '25', 'd': '25', 'e': '25', 'f': '21', 'g': '25', 'h': '25',
        'i': '9', 'j': '17', 'k': '21', 'l': '13', 'm': '33', 'n': '25',
        'o': '25', 'p': '25', 'q': '25', 'r': '21', 's': '21', 't': '21',
        'u': '25', 'v': '25', 'w': '25', 'x': '25', 'y': '25', 'z': '25',
        '{': '21', '|': '9', '}': '21', '~': '25', '¡': '9', '¢': '29', '£': '25',
        '©': '41', '®': '41', '±': '25', '¿': '21', 'À': '25', 'Á': '25',
        'Â': '25', 'Ä': '25', 'Ç': '21', 'È': '21', 'É': '21', 'Ê': '21',
        'Ë': '21', 'Ì': '13', 'Í': '13', 'Î': '17', 'Ï': '17', 'Ñ': '25',
        'Ò': '25', 'Ó': '25', 'Ô': '25', 'Ö': '25', '×': '25', 'Ù': '25',
        'Ú': '25', 'Û': '25', 'Ü': '25', 'ß': '25', 'à': '25', 'á': '25',
        'â': '25', 'ä': '25', 'è': '25', 'é': '25', 'ê': '25', 'ë': '25',
        'ì': '13', 'í': '13', 'î': '17', 'ï': '17', 'ñ': '25', 'ò': '25',
        'ó': '25', 'ô': '25', 'ö': '25', '÷': '25', 'ù': '25', 'ú': '25',
        'û': '25', 'ü': '25', '‘': '13', '’': '13', '“': '21', '”': '21',
        '…': '25', '€': '29', '™': '41', '\x00': '36'}


    # ---- FORMATTING FUNCs
    def get_text_width(self, text, size):
        """ Return an int representing the size of a word

            Requires three dictionaries, defining the width of each char
            for our given font, Nintendo-DS-BIOS.ttf
        """
        if size == 2:
            return sum(int(self.lfDict.get(c, 25)) for c in text)
        elif size == 1:
            return sum(int(self.mfDict.get(c, 12)) for c in text)
        elif size == 0:
            return sum(int(self.sfDict.get(c, 6)) for c in text)


    def format_x_word(self, text_size_list, text_list, size):
        """ Return a list of 'squished' words to fit exact width dimensions

            Parameters:
                text_size_list: a list of ints representing the width of each word
                text_list: a list of strs to be combined as to print neater words
                size: {0, 1, 2} to denote DS font sizes {16, 32, 64}
            Returns:
                new text_list: a list of strs, occasionally combined if possible
        """
        temp_text_list = []
        phrase_width, floor_index = 0, 0
        max_width = 189  # Widest width we will allow as we build word by word
        # Correlation between size{0, 1, 2} and the pixel count of a ' ' char
        space_size = (1 + size // .6) * 2

        for i, word_width in enumerate(text_size_list):
            # Not our last word
            if i != len(text_size_list) - 1:
                # Can fit word in last row
                if phrase_width + word_width + space_size < max_width:
                    phrase_width += word_width + space_size
                # Cannot fit word in last row
                else:
                    temp_text_list.append(" ".join(text_list[floor_index:i]))
                    floor_index, phrase_width = i, word_width
            else:
                # Can fit last word in last row
                if phrase_width + word_width + space_size < max_width:
                    temp_text_list.append(" ".join(text_list[floor_index:i + 1]))
                # Cannot fit last word in last row
                else:
                    # If we have more than one word, seperate prior to current
                    if len(text_list) != 1:
                        temp_text_list.append(" ".join(text_list[floor_index:i]))
                        temp_text_list.append(text_list[i])
                    # Only one word, return whole word to be hypenated later
                    else:
                        temp_text_list.append(text_list[i])
        temp_text_list[:] = [word for word in temp_text_list if word != '']
        return temp_text_list


    def hyphenate_words(self, word, size):
        """ Return a list of 'spliced' word segments to fit exact width dimensions

            Parameters:
                word: our string to hyphenate
                size: {0, 1, 2} to denote DS font sizes {16, 32, 64}
            Returns:
                new text_list: a list of split strs from our word
        """
        temp_text_list = []
        phrase_width, floor_index = 0, 0
        char_size = 0
        max_width = 177  # Widest width we will allow as we build char by char
        # Iterate over every character in the word
        for i, c in enumerate(word):
            # Find relative char width. Will never hyphenate Large text
            if size == 1:
                char_size = int(self.mfDict.get(c, 12))
            elif size == 0:
                char_size = int(self.sfDict.get(c, 25))

            # Our last character
            if len(word) - 1 == i:
                temp_text_list.append(word[floor_index:i + 1])
            # We can add more characters to our split string
            elif phrase_width + char_size < max_width:
                phrase_width += char_size
            # Attach hyphen and start building new split string
            else:
                temp_text_list.append(word[floor_index:i] + "-")
                floor_index, phrase_width = i, char_size
        return temp_text_list


    def can_full_words_fit(self, text_size_list):
        return all(word_len < 189 for word_len in text_size_list)


    # ---- DRAWING FUNCs ----------------------------------------------------------------------------
    def create_time_text(self, img_draw_obj, military_time, date_str, temp_tuple, metric_units, time_on_right, hide_other_weather):
        # Ok but do we need img_draw_obj
        new_draw_obj = Image.new('1', (400, 300), 128)
        draw = ImageDraw.Draw(new_draw_obj)
        self.draw_date_time_temp(draw, military_time, date_str, temp_tuple, metric_units, time_on_right, hide_other_weather)
        if "am" in military_time or "pm" in military_time:
            current_time_width = img_draw_obj.textsize(military_time[:-2], self.DSfnt64)[0]
            current_am_pm_width = img_draw_obj.textsize(military_time[-2:], self.DSfnt32)[0]
            partial_width = current_time_width + current_am_pm_width
        else:
            partial_width = img_draw_obj.textsize(military_time, self.DSfnt64)[0]

        date = dt.now() - timedelta(minutes=1)
        time_str = date.strftime("%-I:%M") + date.strftime("%p").lower() if "am" in military_time or "pm" in military_time else date.strftime("%-H:%M")
        if "am" in time_str or "pm" in time_str:
            current_time_width = img_draw_obj.textsize(time_str[:-2], self.DSfnt64)[0]
            current_am_pm_width = img_draw_obj.textsize(time_str[-2:], self.DSfnt32)[0]
            old_partial_width = current_time_width + current_am_pm_width
        else:
            old_partial_width = img_draw_obj.textsize(time_str, self.DSfnt64)[0]

        # unclear why this must be present... but without it we are always incorrectly inverted
        new_draw_obj = ImageMath.eval('255-(a)', a=new_draw_obj)

        return new_draw_obj, max(partial_width, old_partial_width) + 3


    def draw_border_lines(self, img_draw_obj):
        # draw vertical and horizontal lines of width 3
        for i in range(3):
            img_draw_obj.line([(0, 224 + i), (400, 224 + i)], fill=0)
            img_draw_obj.line([(199 + i, 0), (199 + i, 225)], fill=0)


    def draw_name(self, img_draw_obj, text, name_x, name_y):
        name_width, name_height = img_draw_obj.textsize(text, font=self.helveti32)
        img_draw_obj.text((name_x, name_y), text, font=self.helveti32)
        line_start_x, line_start_y = name_x - 1, name_y + name_height + 3
        line_end_x, line_end_y = name_x + name_width - 1, name_y + name_height + 3
        img_draw_obj.line([(line_start_x, line_start_y), (line_end_x, line_end_y)], fill=0)
        return name_width, name_height


    def draw_user_time_ago(self, img_draw_obj, text, time_x, time_y):
        # draw text next to name displaying time since last played track
        time_width, time_height = img_draw_obj.textsize(text, font=self.DSfnt16)
        img_draw_obj.text((time_x, time_y), text, font=self.DSfnt16)


    def draw_spot_context(self, img_draw_obj, new_draw_obj, context_type, context_text, context_x, context_y):
        # Draws both icon {playlist, album, artist} and context text in the bottom of Spot box
        if context_type is not None:
            context_width, temp_context = 0, ""
            # make sure we don't run past context width requirements
            for c in context_text:
                char_width = int(self.sfDict.get(c, 6))
                if context_width + char_width < 168:
                    context_width += char_width
                    temp_context += c
                else:
                    temp_context += "..."
                    break
            img_draw_obj.text((context_x, context_y), temp_context, font=self.DSfnt16)

            # ATTACH ICONS
            if context_type == 'playlist':
                new_draw_obj.paste(self.playlist_icon, (context_x - 21, context_y - 1))
            elif context_type == 'album':
                new_draw_obj.paste(self.album_icon, (context_x - 24, context_y - 4))
            elif context_type == 'artist':
                new_draw_obj.paste(self.artist_icon, (context_x - 22, context_y - 1))


    def draw_album_image(self, img_draw_obj, image_file_name, dark_mode):
        album_image = Image.open(image_file_name)
        if dark_mode:
            album_image = album_image.convert("1")
            album_image = ImageMath.eval('255-(a)', a=album_image)
        img_draw_obj.paste(album_image, (0, 0))

    def draw_weather(self, img_draw_obj, pos, temp_tuple, metric_units):
        temp, temp_high, temp_low, other_temp = temp_tuple
        temp_degrees = "C" if metric_units else "F"

        # main temp pos calculations
        temp_start_x = pos[0]
        temp_width = img_draw_obj.textsize(str(temp), font=self.DSfnt64)[0]

        # forcast temp pos calculations
        temp_high_width = self.get_text_width(str(temp_high), 1)
        temp_low_width = self.get_text_width(str(temp_low), 1)
        forcast_temp_x = temp_start_x + temp_width + 18 + max(temp_low_width, temp_high_width)

        # I found that negative temps widen the formatting. This 'fixes' that issue 
        if temp_high < 0 or temp_low < 0:
            forcast_temp_x -= 5

        # draw main temp
        img_draw_obj.text(pos, str(temp), font=self.DSfnt64)
        img_draw_obj.text((temp_start_x + temp_width, 245), temp_degrees, font=self.DSfnt32)

        # draw forcast temp
        img_draw_obj.text((forcast_temp_x - temp_high_width, 242), str(temp_high), font=self.DSfnt32)
        img_draw_obj.text((forcast_temp_x + 2, 244), temp_degrees, font=self.DSfnt16)
        img_draw_obj.text((forcast_temp_x - temp_low_width, 266), str(temp_low), font=self.DSfnt32)
        img_draw_obj.text((forcast_temp_x + 2, 268), temp_degrees, font=self.DSfnt16)


    def draw_time(self, img_draw_obj, pos, time):
        if "am" in time or "pm" in time:
            am_pm = time[-2:]
            current_time = time[:-2]

            # am_pm pos calculations
            am_pm_x = pos[0] + img_draw_obj.textsize(current_time, font=self.DSfnt64)[0]

            # draw time + am_pm
            img_draw_obj.text(pos, current_time, font=self.DSfnt64)
            img_draw_obj.text((am_pm_x, pos[1] + 22), am_pm, font=self.DSfnt32)
        else:
            # draw time
            img_draw_obj.text(pos, time, font=self.DSfnt64)

    def draw_date_time_temp(self, img_draw_obj, military_time, date_str, temp_tuple, metric_units, time_on_right, hide_other_weather):
        temp, temp_high, temp_low, other_temp = temp_tuple
        temp_degrees = "C" if metric_units else "F"
        left_elem_x = 10

        # the height of the bottom bar
        bar_height = 74

        if time_on_right:
            # main temp pos calculations
            temp_width, temp_height = img_draw_obj.textsize(str(temp), font=self.DSfnt64)
            left_elem_y = self.HEIGHT - (bar_height // 2) - (temp_height // 2)
            left_elem_pos = (left_elem_x, left_elem_y)

            self.draw_weather(img_draw_obj, left_elem_pos, temp_tuple, metric_units)

            # draw time on the right side of screen after deciding 24H or AM_PM
            if "am" in military_time or "pm" in military_time:
                # time pos calculations; add width of am_pm too
                time_width, time_height = img_draw_obj.textsize(str(military_time[:-2]), font=self.DSfnt64)
                time_width += img_draw_obj.textsize(str(military_time[-2:]), font=self.DSfnt32)[0]
            else:
                # time pos calculations without am_pm
                time_width, time_height = img_draw_obj.textsize(military_time, self.DSfnt64)
            right_elem_x = self.WIDTH - time_width - 5
            right_elem_y = self.HEIGHT - (bar_height // 2) - (time_height // 2)
            right_elem_pos = (right_elem_x, right_elem_y)

            self.draw_time(img_draw_obj, right_elem_pos, military_time)

        else:
            # draw time on the left screen after deciding 24H or AMPM
            if "am" in military_time or "pm" in military_time:
                # time pos calculations; add width of am_pm too
                time_width, time_height = img_draw_obj.textsize(str(military_time[:-2]), font=self.DSfnt64)
                time_width += img_draw_obj.textsize(str(military_time[-2:]), font=self.DSfnt32)[0]
            else:
                # time pos calculations
                time_width, time_height = img_draw_obj.textsize(military_time, font=self.DSfnt64)
            left_elem_y = self.HEIGHT - (bar_height // 2) - (time_height // 2)
            left_elem_pos = (left_elem_x, left_elem_y)

            self.draw_time(img_draw_obj, left_elem_pos, military_time)

            temp_width, temp_height = img_draw_obj.textsize(str(temp), font=self.DSfnt64)
            forcast_temp_x = temp_width + 20
            temp_high_width, temp_low_width = self.get_text_width(str(temp_high), 1), self.get_text_width(str(temp_high), 1)
            right_elem_x = self.WIDTH - (forcast_temp_x + max(temp_high_width, temp_low_width) + 12)
            right_elem_y = self.HEIGHT - (bar_height // 2) - (temp_height // 2)
            right_elem_pos = (right_elem_x, right_elem_y)

            self.draw_weather(img_draw_obj, right_elem_pos, temp_tuple, metric_units)

        # draw the date in the center of the bottom bar
        date_width, date_height = img_draw_obj.textsize(date_str, font=self.DSfnt32)  
        date_x =  left_elem_x + time_width + (right_elem_x - left_elem_x - time_width) // 2 - date_width // 2
        date_y = 239 + date_height
        img_draw_obj.text((date_x, date_y), date_str, font=self.DSfnt32)

        # Draw "upper temp" next to name of right user
        if not hide_other_weather:
            high_temp_x = 387 - self.get_text_width(str(other_temp), 1)
            img_draw_obj.text((high_temp_x, 0), str(other_temp), font=self.DSfnt32)
            img_draw_obj.text((high_temp_x + 2 + self.get_text_width(str(other_temp), 1), 2), temp_degrees, font=self.DSfnt16)


    def draw_track_text(self, img_draw_obj, track_name, track_x, track_y):
        # After deciding the size of text, split words into lines, and draw to img_draw_obj

        # Large Text Format Check
        l_title_split = track_name.split(" ")
        l_title_size = list(map(self.get_text_width, l_title_split, [2] * len(l_title_split)))
        track_lines = self.format_x_word(l_title_size, l_title_split, 2)
        track_size = list(map(self.get_text_width, track_lines, [2] * len(l_title_split)))
        if sum(track_size) <= 378 and self.can_full_words_fit(track_size) and len(track_size) <= 2:
            for line in track_lines:
                img_draw_obj.text((track_x, track_y), line, font=self.DSfnt64)
                track_y += 43
            return len(track_lines), 55

        # Medium Text Format Check
        m_title_split = []
        if len(track_name.split(" ")) > 1:
            m_title_split = track_name.split(" ")
        else:
            m_title_split.append(track_name)
        m_title_size = list(map(self.get_text_width, m_title_split, [1] * len(m_title_split)))
        track_lines = self.format_x_word(m_title_size, m_title_split, 1)
        track_size = list(map(self.get_text_width, track_lines, [1] * len(track_lines)))
        if sum(track_size) <= 945:
            if not self.can_full_words_fit(track_size):
                track_lines = hyphenate_words(str(m_title_split)[2:-2], 1)
            for line in track_lines:
                img_draw_obj.text((track_x, track_y), line, font=self.DSfnt32)
                track_y += 26
            return len(track_lines), 26

        # Small Text Format Check
        s_title_split = []
        if len(track_name.split(" ")) > 1:
            s_title_split = track_name.split(" ")
        else:
            s_title_split.append(track_name)
        s_title_size = list(map(self.get_text_width, s_title_split, [0] * len(s_title_split)))
        track_lines = self.format_x_word(s_title_size, s_title_split, 0)
        track_size = list(map(self.get_text_width, track_lines, [1] * len(s_title_split)))
        track_y += 5
        if not self.can_full_words_fit(s_title_size):
            track_lines = hyphenate_words(str(s_title_split)[2:-2], 1)
        for line in track_lines:
            img_draw_obj.text((track_x, track_y), line, font=self.DSfnt16)
            track_y += 12
        return len(track_lines), 13


    def draw_artist_text(self, img_draw_obj, artist_name, track_line_count, track_height, artist_x, artist_y):
        # Always ensure bottom of text is always at 190 pixels after draw height

        # Large Text Format Check
        l_artist_split = artist_name.split(" ")
        l_artist_size = list(map(self.get_text_width, l_artist_split, [2] * len(l_artist_split)))
        if sum(l_artist_size) <= 366 and self.can_full_words_fit(l_artist_size) and len(l_artist_size) <= 2:
            if track_height == 55 and track_line_count + len(l_artist_size) <= 3 or track_height < 55 and track_line_count < 4:
                artist_lines = self.format_x_word(l_artist_size, l_artist_split, 2)
                artist_y = 190 - (42 * len(artist_lines))  # y nudge to fit bottom constraint
                for line in artist_lines:
                    img_draw_obj.text((artist_x, artist_y), line, font=self.DSfnt64)
                    artist_y += 43
                return

        # Medium Text Format Check
        m_artist_split = []
        if len(artist_name.split(" ")) > 1:
            m_artist_split = artist_name.split(" ")
        else:
            m_artist_split.append(artist_name)
        m_title_size = list(map(self.get_text_width, m_artist_split, [1] * len(m_artist_split)))
        artist_lines = self.format_x_word(m_title_size, m_artist_split, 1)
        artist_size = list(map(self.get_text_width, artist_lines, [1] * len(m_artist_split))) 
        if sum(artist_size) <= 760 and track_line_count + len(artist_lines) <= 6:
            artist_y = 190 - (25 * len(artist_lines))  # y nudge to fit bottom constraint
            if not self.can_full_words_fit(m_title_size):
                artist_lines = hyphenate_words(str(m_artist_split)[2:-2], 1)
            for line in artist_lines:
                img_draw_obj.text((artist_x, artist_y), line, font=self.DSfnt32)
                artist_y += 26
            return

        # Small Text Format Check
        s_artist_split = []
        if len(artist_name.split(" ")) > 1:
            s_artist_split = artist_name.split(" ")
        else:
            s_artist_split.append(artist_name)
        s_artist_size = list(map(self.get_text_width, s_artist_split, [0] * len(s_artist_split)))
        artist_lines = self.format_x_word(s_artist_size, s_artist_split, 0)
        artist_size = list(map(self.get_text_width, artist_lines, [0] * len(s_artist_split)))
        artist_y = 190 - (12 * len(artist_lines))  # y nudge to fit bottom constraint
        if not self.can_full_words_fit(s_artist_size):
            artist_lines = hyphenate_words(str(s_artist_split)[2:-2], 1)
        for line in artist_lines:
            img_draw_obj.text((artist_x, artist_y), line, font=self.DSfnt16)
            artist_y += 12


class LocalJsonIO():
    def write_json_ctx(self, left_ctx, right_ctx):
        """ creates, writes to context.txt a json object containing the ctx of left and right users. """

        # if we have already written context info, don't rewrite file
        left_temp_ctx, right_tmp_ctx = left_ctx, right_ctx
        try:
            with open('context.txt') as j_ctx:
                write_l_ctx, write_r_ctx = True, True
                data = json.load(j_ctx)

                # check left ctx, assign tmp ctx if our pulled data is new
                if left_ctx[0] == data['context'][0]['type'] and left_ctx[1] == data['context'][0]['title']:
                    write_l_ctx = False
                # check right ctx, assign tmp ctx if our pulled data is new
                if right_ctx[0] == data['context'][1]['type'] and right_ctx[1] == data['context'][1]['title']:
                    write_r_ctx = False

                if not write_l_ctx and not write_r_ctx:
                    return
                print("Update context.txt")
                print("left_ctx: {} right_ctx: {}".format(left_ctx, right_ctx))
        except Exception as e:
            print("write_json_ctx() Failed:", e)
            print("writing to new context.txt")

        context_data = {}
        context_data['context'] = []
        # attach left ctx
        context_data['context'].append({
                'position': 'left',
                'type': left_temp_ctx[0],
                'title': left_temp_ctx[1]
        })
        # attach right ctx
        context_data['context'].append({
            'position': 'right',
            'type': right_tmp_ctx[0],
            'title': right_tmp_ctx[1]
        })

        with open('context.txt', 'w+') as j_cxt:
            json.dump(context_data, j_cxt)


    def read_json_ctx(self, left_ctx, right_ctx):
        """ Read context.txt, returning ctx found if left_ctx, or right_ctx is empty. """
        with open('context.txt') as j_cxt:
            context_data = json.load(j_cxt)
            data = context_data['context']
            # Only update an empty context side. Either update the left ctx, the right ctx, or both ctx files
            if left_ctx[0] != "" and left_ctx[1] != "" and right_ctx[0] == "" and right_ctx[1] == "":
                return left_ctx[0], left_ctx[1], data[1]['type'], data[1]['title']
            elif left_ctx[0] == "" and left_ctx[1] == "" and right_ctx[0] != "" and right_ctx[1] != "":
                return data[0]['type'], data[0]['title'], right_ctx[0], right_ctx[1]
            else:
                return data[0]['type'], data[0]['title'], data[1]['type'], data[1]['title']

if __name__ == '__main__':
    # local_test is for debugging. If local_test is true, show the EPD image locally 
    # local test ignores dark mode
    local_test = False
    if not local_test:
        main_loop()
    else:
        start = time()
        epd_draw = DrawToEPD()

        temp_tuple = getWeather(metric_units)
        seconds_left, military_time, date_str = getTimeFromDatetime(twenty_four_clock)

        # CREATE BLANK IMAGE
        Himage = Image.new('1', (WIDTH, HEIGHT), 128)
        draw = ImageDraw.Draw(Himage)

        # DRAW LINES DATE TIME TEMP ----------------------------------------------------------------
        epd_draw.drawBoarderLines(draw)
        epd_draw.drawDateTimeTemp(draw, military_time, date_str, temp_tuple, metric_units)

        # GET Left's SPOTIPY AUTH OBJECT, TOKEN ----------------------------------------------------------------
        l_oauth = spotipy.oauth2.SpotifyOAuth(l_spot_client_id, l_spot_client_secret, REDIRECT_URI, scope = SCOPE, cache_path = l_cache, requests_timeout = 10)
        l_token_info = l_oauth.get_cached_token()
        l_token = getSpotipyToken(l_oauth, l_token_info)
        if l_token:
            print("Left's access token available")
            l_track, l_artist, l_time_since, l_ctx_type, l_ctx_title = getSpotipyInfo(l_token)
        else:
            print(":( Left's access token unavailable")
            l_track, l_artist = "", ""

        # GET Right's SPOTIFY TOKEN
        r_oauth = spotipy.oauth2.SpotifyOAuth(r_spot_client_id, r_spot_client_secret, REDIRECT_URI, scope = SCOPE, cache_path = r_cache, requests_timeout = 10)
        r_token_info = r_oauth.get_cached_token()
        r_token = getSpotipyToken(r_oauth, r_token_info)
        if r_token:
            r_track, r_artist, r_time_since, temp_context_type, temp_context_name = getSpotipyInfo(r_token)
            r_ctx_type = temp_context_type if temp_context_type != "" else r_ctx_type
            r_ctx_title = temp_context_name if temp_context_name != "" else r_ctx_title
        else:
            print(":( Right's access token unavailable")
            r_track, r_artist = "", ""

        # USER 1 & 2 TRACK TITLES CONTEXT ----------------------------------------------------------------
        track_line_count, track_text_size = drawTrackText(draw, l_track, 5, 26)
        drawArtistText(draw, l_artist, track_line_count, track_text_size, 5, 26)
        drawSpotContext(draw, Himage, l_ctx_type, l_ctx_title, 25, 204)
        track_line_count, track_text_size = drawTrackText(draw, r_track, 207, 26)
        drawArtistText(draw, r_artist, track_line_count, track_text_size, 207, 26)
        drawSpotContext(draw, Himage, r_ctx_type, r_ctx_title, 227, 204)

        # NAMES ----------------------------------------------------------------
        l_name_width, l_name_height = drawName(draw, "Batman", 8, 0)
        drawUserTimeAgo(draw, l_time_since, 18 + l_name_width, l_name_height // 2)
        r_name_width, r_name_height = drawName(draw, "Robin", 210, 0)
        drawUserTimeAgo(draw, r_time_since, 220 + r_name_width, r_name_height // 2) 

        # HIDDEN DARK MODE 
        # Himage = ImageMath.eval('255-(a)',a=Himage)
        Himage.show()

        stop = time()
        time_elapsed = stop - start
        print("Completed in {} seconds".format(time_elapsed))




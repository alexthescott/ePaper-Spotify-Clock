#!/usr/bin/python3
# -*- coding:utf-8 -*-

""" spotify_epd.py by Alex Scott 2020

Made for the Waveshare 4.2inch e-Paper Module
https://www.waveshare.com/wiki/4.2inch_e-Paper_Module

This program finds the last thing two people listened to on Spotify, and 
displays the track title, artist name, and context.

In addition, this program uses the OpenWeatherMap api to retrieve and
display the current 'feels-like' temperature, along with the date and time

6:00am - 8:00pm the display updates every 3 minutes
8:00pm - 12:00pm the display updates every 5 minutes
12:00pm - 2:00am the display updates every 15 minutes
2:00am - 6:00am the display does not update
This is all in an effort to ensure the display does not see long term damage

A preview of the end result can be found here:
https://raw.githubusercontent.com/alexthescott/4.2in-ePaper-Spotify-Clock/master/spotify_epaper_preview.jpg

This program is intended to be used along with a bash script which re-launches the program
in the event of a crash. That bash script can be found here:
https://github.com/alexthescott/4.2in-ePaper-Spotify-Clock/blob/master/launch_epaper.sh
"""

import spotipy
from time import time, sleep
from random import randint
from datetime import timedelta, datetime as dt
from requests import get as getRequest
from waveshare_epd import epd4in2
from PIL import Image, ImageDraw, ImageMath

# Local .py dependencies
import localJsonIO as contextIO
import drawToEPD as epdDraw

def mainLoop():
    epd = epd4in2.EPD()
    WIDTH, HEIGHT = epd.width, epd.height
    r_ctx_type, r_ctx_title, l_ctx_type, l_ctx_title = "", "", "", ""

    time_elapsed = 15.0
    old_time, temp_tuple = None, None

    # countTo5 is used to get weather every 5 minutes
    countTo5 = 0 

    # First loop, init EPD
    DID_EPD_INIT = False

    try:
        while True:
            # Get time variables. old_time is used to ensure even time difference intervals between updates
            sec_left, time_str, date_str, old_time = getTimeFromDatetime(time_elapsed, old_time)
            print(time_str)

            # Firstly, this is for my own edifice to know how long a loop takes for the Pi
            # Secondly, this is used to 'push' our clock forward such that our clock update is exactly on time
            start = time()
            
            # OPENWEATHER API CALL
            if temp_tuple == None or countTo5 == 4:
                temp_tuple = getWeather()

            # CREATE BLANK IMAGE
            Himage = Image.new('1', (WIDTH, HEIGHT), 128)
            draw = ImageDraw.Draw(Himage)

            # GET left user's SPOTIPY AUTH OBJECT, TOKEN
            print("Get left user's Spotify Token")
            l_oauth = spotipy.oauth2.SpotifyOAuth(l_spot_client_id, l_spot_client_secret, REDIRECT_URI, scope = SPOT_SCOPE, cache_path = l_cache, requests_timeout = 10)
            l_token_info = l_oauth.get_cached_token()
            l_token = getSpotipyToken(l_oauth, l_token_info)
            if l_token:
                l_track, l_artist, l_time_since, temp_context_type, temp_context_name = getSpotipyInfo(l_token)
                l_ctx_type = temp_context_type if temp_context_type != "" else l_ctx_type
                l_ctx_title = temp_context_name if temp_context_name != "" else l_ctx_title
            else:
                print(":( Left's access token unavailable")
                l_track, l_artist = "", ""

            # GET right user's SPOTIFY TOKEN
            print("Get right user's Spotify Token")
            r_oauth = spotipy.oauth2.SpotifyOAuth(r_spot_client_id, r_spot_client_secret, REDIRECT_URI, scope = SPOT_SCOPE, cache_path = r_cache, requests_timeout = 10)
            r_token_info = r_oauth.get_cached_token()
            r_token = getSpotipyToken(r_oauth, r_token_info)
            if r_token:
                r_track, r_artist, r_time_since, temp_context_type, temp_context_name = getSpotipyInfo(r_token)
                r_ctx_type = temp_context_type if temp_context_type != "" else r_ctx_type
                r_ctx_title = temp_context_name if temp_context_name != "" else r_ctx_title
            else:
                print(":( Right's access token unavailable")
                r_track, r_artist = "", ""

            # If we have no context read, grab context our context.txt json file 
            if l_ctx_type == "" and l_ctx_title == "" or r_ctx_type == "" and r_ctx_title == "":
                l_ctx_type, l_ctx_title, r_ctx_type, r_ctx_title = contextIO.readJsonContext((l_ctx_type,l_ctx_title), (r_ctx_type,r_ctx_title))
            # Afterwords, if we have to write a new context to our context.txt json file, do so
            if l_ctx_type != "" and l_ctx_title != "" or r_ctx_type != "" and r_ctx_title != "":
                contextIO.writeJsonContext((l_ctx_type,l_ctx_title), (r_ctx_type,r_ctx_title))

            # USER 1 & 2 TRACK TITLES CONTEXT ----------------------------------------------------------------
            track_line_count, track_text_size = epdDraw.drawTrackText(draw, l_track, 5, 26)
            epdDraw.drawArtistText(draw, l_artist, track_line_count, track_text_size, 5, 26)
            epdDraw.drawSpotContext(draw, Himage, l_ctx_type, l_ctx_title, 25, 204)      

            track_line_count, track_text_size = epdDraw.drawTrackText(draw, r_track, 207, 26)
            epdDraw.drawArtistText(draw, r_artist, track_line_count, track_text_size, 207, 26)
            epdDraw.drawSpotContext(draw, Himage, r_ctx_type, r_ctx_title, 227, 204)

            # DRAW NAMES TIME SINCE ----------------------------------------------------------------
            l_name_width, l_name_height = epdDraw.drawName(draw, "Batman", 8, 0)
            epdDraw.drawUserTimeAgo(draw, l_time_since, 18 + l_name_width, l_name_height // 2)
            r_name_width, r_name_height = epdDraw.drawName(draw, "Robin", 210, 0)
            epdDraw.drawUserTimeAgo(draw, r_time_since, 220 + r_name_width, r_name_height // 2) 

            # DRAW LINES DATE TIME TEMP ----------------------------------------------------------------
            epdDraw.drawBorderLines(draw)
            epdDraw.drawDateTimeTemp(draw, time_str, date_str, temp_tuple)

            # HIDDEN DARK MODE
            # Himage = ImageMath.eval('255-(a)',a=Himage)

            # from 2 - 5:59am, don't init the display, return from main, and have .sh script run again in 3 mins
            hour = int(time_str.split(":")[0])
            if (time_str[-2:] == 'am' and (hour >= 2 and hour <= 5)):
                if DID_EPD_INIT == True:
                    # in sleep() from epd4in2.py, epdconfig.module_exit() is never called
                    # I hope this does not create long term damage 🤞 
                    print("EPD Sleep(ish) ....")
                    break
                else:
                    print("Don't Wake")
                    break
            elif DID_EPD_INIT == False:
                print("EPD INIT")
                epd.init()
                epd.Clear()
                DID_EPD_INIT = True

            if DID_EPD_INIT:
                image_buffer = epd.getbuffer(Himage)
                print("\tDrawing Image to EPD")
                epd.display(image_buffer)

            # Look @ start variable above. find out how long it takes to compute our image
            stop = time()
            time_elapsed = stop - start

            remaining_time = sec_left - time_elapsed
            if remaining_time < 0: remaining_time = 60

            if (time_str[-2:] == 'am' and (hour >= 6 and hour != 12)) or (time_str[-2:] == 'pm' and hour <= 12):
                # 6:00am - 11:59pm update screen every 3 minutes
                print("\t", round(time_elapsed, 2), "\tseconds per loop\t", "sleeping for {} seconds".format(int(remaining_time) + 120))
                sleep(remaining_time + 120)
            elif (time_str[-2:] == 'am' and (hour < 2 or hour == 12)):
                # 12:00am - 1:59am update screen every 5ish minutes
                print("\t", round(time_elapsed, 2), "\tseconds per loop\t", "sleeping for {} seconds".format(int(remaining_time) + 240))
                sleep(remaining_time + 240)

            # Increment counter for Weather requests
            countTo5 = 0 if countTo5 == 4 else countTo5 + 1

    except Exception as e:
        with open("bugs.txt", "a+") as error_file:
            file_text = error_file.read()
            if str(e) in file_text:
                print("bug already caught")
            else:
                print("new bug caught\n" + str(e))
                error_file.write(str(e) + "\n")
        print("Retrying mainLoop() in 20 seconds...")
        sleep(20)
        mainLoop()

# Spotify Functions
def getSpotipyToken(sp_oauth, token_info):
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
            token = sp_oauth['access_token']
    return token
def getSpotipyInfo(token):
    # GRAB CURRENT OR RECENT TRACK OBJECT
    sp = spotipy.Spotify(auth=token)
    recent = sp.current_user_playing_track()
    context_type, context_name, time_passed = "", "", ""
    if recent != None and recent['item'] != None:
        # GET CURRENT CONTEXT
        context_type, context_name = getContextFromJson(recent['context'], sp)

        # GET TRACK && ARTIST
        track_name, artists = recent['item']['name'], recent['item']['artists']
        artist_name = ""
        for i in range(len(artists)):
            artist_name += artists[i]['name'] + ", "
        artist_name = artist_name[:-2]

        time_passed = " is listening to"
    else:
        # GRAB OLD CONTEXT
        recent = sp.current_user_recently_played(1)
        tracks = recent["items"]
        track = tracks[0]
        track_name, artists = track['track']['name'], track['track']['artists']
        # Concatinate artist names
        artist_name = ""
        for i in range(len(artists)):
            artist_name += track['track']['artists'][i]['name'] + ", "
        artist_name = artist_name[:-2]

        last_timestamp = track['played_at']
        str_timestamp = last_timestamp[:10] + " " + last_timestamp[11:19]
        timestamp = dt.strptime(str_timestamp, "%Y-%m-%d %H:%M:%S")
        hours_passed, minutes_passed = getTimeFromTimeDelta(dt.utcnow() - timestamp)
        time_passed = getTimeSincePlayed(hours_passed, minutes_passed)
        context_type, context_name = getContextFromJson(track['context'], sp)
    return track_name, artist_name, time_passed, context_type, context_name 
def getContextFromJson(context_json, spotipy_object):
    context_type, context_name = "", ""
    if context_json != None:
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
def getTimeFromDatetime(time_elapsed, oldMinute):
    # Returns seconds, time, date, and the minute of update
    # We halt until a proper time window has passed
    date = dt.now() + timedelta(seconds = time_elapsed) 
    am_pm = date.strftime("%p")
    time_str = date.strftime("%-I:%M") + am_pm.lower()
    hour = int(time_str.split(":")[0])
    newMinute = int(date.strftime("%M")[-1])

    # Here we make some considerations so the screen isn't updated too frequently
    # We air on the side of caution, and would rather add an additional minute than shrink by a minute
    if oldMinute != None and ((time_str[-2:] == 'am' and (hour >= 6 and hour != 12)) or (time_str[-2:] == 'pm' and hour <= 12)):
        # 6:00am - 11:59pm update screen every 3 mins
        while int(abs(oldMinute - newMinute)) < 3:
            date = dt.now() + timedelta(seconds = time_elapsed)
            newMinute = int(date.strftime("%M")[-1])
            sleep(2)
    # 12:00am - 1:59am update screen every 5 mins at least
    elif oldMinute != None and (time_str[-2:] == 'am' and (hour < 2 or hour == 12)):
        while int(abs(oldMinute - newMinute)) < 5:
            date = dt.now() + timedelta(seconds = time_elapsed)
            newMinute = int(date.strftime("%M")[-1])
            sleep(2)
    # 2:00am - 5:59am check time every 15ish minutes, granularity here is not paramount
    sec_left = 60 - int(date.strftime("%S")) 
    date_str, am_pm = date.strftime("%a, %b %-d"), date.strftime("%p")
    time_str = date.strftime("%-I:%M") + am_pm.lower()
    return sec_left, time_str, date_str, int(newMinute)
def getTimeFromTimeDelta(td):
    # Returns hours and minutes as ints
    return td.days * 24 + td.seconds // 3600, (td.seconds % 3600) // 60
def getTimeSincePlayed(hours, minutes):
    # From the hours and minutes passed, return a string representation  
    if hours == 0 and minutes <=4: 
        return " is listening to"
    elif hours == 0: 
        return str(minutes - (minutes%5)) + "  minutes ago"
    elif hours == 1: 
        return str(hours) + "  hour ago"
    elif hours < 24: 
        return str(hours) + "  hours ago"
    elif 24 <= hours and hours > 24: 
        return str(hours // 24) + "  day ago"
    else: 
        return str(hours // 24) + "  days ago"

def getWeather():
    OW_KEY = "" # https://openweathermap.org/
    OW_CITYID = "" 
    OW_OTHER_CITYID = "" 

    # Get current weather
    OW_CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather?"
    OW_CURRENT_COMPLETE = OW_CURRENT_URL + "appid=" + OW_KEY + "&id=" + OW_CITYID + "&units=imperial"
    weather_response = getRequest(OW_CURRENT_COMPLETE)
    weather_json = weather_response.json()
    if weather_json["cod"] != "404":
        temp = round(weather_json['main']['feels_like'])
        temp_min, temp_max = temp, temp

    # get current weather for user on the right
    OW_CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather?"
    OW_CURRENT_COMPLETE = OW_CURRENT_URL + "appid=" + OW_KEY + "&id=" + OW_OTHER_CITYID + "&units=imperial"
    weather_response = getRequest(OW_CURRENT_COMPLETE)
    weather_json = weather_response.json()
    if weather_json["cod"] != "404":
        other_temp = round(weather_json['main']['feels_like'])

    # Get forecasted weather from feels_like and temp_min, temp_max
    OW_FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast?"
    OW_FORECAST_COMPLETE = OW_FORECAST_URL + "appid=" + OW_KEY + "&id=" + OW_CITYID + "&units=imperial" + "&cnt=12"
    weather_response = getRequest(OW_FORECAST_COMPLETE)
    forecast_json = weather_response.json()
    if forecast_json["cod"] != "404":
        for i, l in enumerate(forecast_json['list']):
            i_temp = round(l['main']['feels_like'])
            max_predicted = max(i_temp, round(l['main']['temp_min']))
            min_predicted = min(i_temp, round(l['main']['temp_max']))
            if temp_min > min_predicted: temp_min = min_predicted
            if temp_max < max_predicted: temp_max = max_predicted
    return temp, temp_max, temp_min, other_temp

if __name__ == '__main__':
    # UNIVERSAL SPOTIPY VARS 
    SPOT_SCOPE = "user-read-private, user-read-recently-played, user-read-playback-state, user-read-currently-playing" 
    REDIRECT_URI = 'http://www.google.com/'

    # Generate Spotify clinet_id and client_secret @ https://developer.spotify.com/dashboard/

    # Left SPOTIPY 
    l_spot_client_id = ''
    l_spot_client_secret = ''
    l_cache = '.leftauthcache'
    l_username = ''

    # Right SPOTIPY 
    r_spot_client_id = ''
    r_spot_client_secret = ''
    r_cache = '.rightauthcache'
    r_username = ''
    mainLoop()

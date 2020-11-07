#!/usr/bin/python3
# -*- coding:utf-8 -*-

""" spotify_epd.py by Alex Scott 2020

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

This program is intended to be used along with a bash script which re-launches the program
in the event of a crash. That bash script can be found here:
https://github.com/alexthescott/4.2in-ePaper-Spotify-Clock/blob/master/launch_epaper.sh
"""

import spotipy
from time import time, sleep, strftime, localtime
from random import randint
from datetime import timedelta, datetime as dt
from requests import get as getRequest
from waveshare_epd import epd4in2
from PIL import Image, ImageDraw, ImageMath

# Local .py dependencies
import localJsonIO as contextIO
import drawToEPD as epdDraw

def mainLoop():
    metric_units = False
    twenty_four_clock = False

    epd = epd4in2.EPD()
    WIDTH, HEIGHT = epd.width, epd.height
    r_ctx_type, r_ctx_title, l_ctx_type, l_ctx_title = "", "", "", ""

    time_elapsed = 15.0
    old_time, temp_tuple = None, None

    # countTo5 is used to get weather every 5 minutes
    countTo5 = 0 
    sunset_time_tuple = None

    # First loop, init EPD
    DID_EPD_INIT = False

    try:
        while True:
            # Get time variables. old_time is used to ensure even time difference intervals between updates
            sec_left, time_str, date_str, old_time = getTimeFromDatetime(time_elapsed, old_time, twenty_four_clock)
            print(time_str)

            # Firstly, this is for my own edifice to know how long a loop takes for the Pi
            # Secondly, this is used to 'push' our clock forward such that our clock update is exactly on time
            start = time()
            
            # OPENWEATHER API CALL
            if temp_tuple == None or countTo5 == 4:
                temp_tuple, sunset_time_tuple = getWeather(metric_units)

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
            if (l_ctx_type == "" and l_ctx_title == "") or (r_ctx_type == "" and r_ctx_title == ""):
                try:
                    fh = open('context.txt')
                    l_ctx_type, l_ctx_title, r_ctx_type, r_ctx_title = contextIO.readJsonContext((l_ctx_type,l_ctx_title), (r_ctx_type,r_ctx_title))
                    fh.close()
                except:
                    print("context.txt doesn't exist")
            # Afterwords, if we have to write a new context to our context.txt json file, do so
            if (l_ctx_type != "" and l_ctx_title != "") or (r_ctx_type != "" and r_ctx_title != ""):
                contextIO.writeJsonContext((l_ctx_type,l_ctx_title), (r_ctx_type,r_ctx_title))

            # USER 1 & 2 TRACK TITLES CONTEXT ----------------------------------------------------------------
            track_line_count, track_text_size = epdDraw.drawTrackText(draw, l_track, 5, 26)
            epdDraw.drawArtistText(draw, l_artist, track_line_count, track_text_size, 5, 26)
            epdDraw.drawSpotContext(draw, Himage, l_ctx_type, l_ctx_title, 25, 204)      

            track_line_count, track_text_size = epdDraw.drawTrackText(draw, r_track, 207, 26)
            epdDraw.drawArtistText(draw, r_artist, track_line_count, track_text_size, 207, 26)
            epdDraw.drawSpotContext(draw, Himage, r_ctx_type, r_ctx_title, 227, 204)

            # DRAW NAMES TIME SINCE ----------------------------------------------------------------
            l_name_width, l_name_height = epdDraw.drawName(draw, "Alex", 8, 0)
            epdDraw.drawUserTimeAgo(draw, l_time_since, 18 + l_name_width, l_name_height // 2)
            r_name_width, r_name_height = epdDraw.drawName(draw, "Emma", 210, 0)
            epdDraw.drawUserTimeAgo(draw, r_time_since, 220 + r_name_width, r_name_height // 2) 

            # DRAW LINES DATE TIME TEMP ----------------------------------------------------------------
            epdDraw.drawBorderLines(draw)
            epdDraw.drawDateTimeTemp(draw, time_str, date_str, temp_tuple, metric_units)

            # Get 24H clock current_hour to determine sleep duration before refresh
            date = dt.now() + timedelta(seconds = time_elapsed)
            current_hour = int(date.strftime("%-H"))
            current_minute = int(date.strftime("%-M"))

            # from 2:01 - 5:59am, don't init the display, return from main, and have .sh script run again in 3 mins
            if 2 <= current_hour and current_hour <= 5:
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
                sunsetTimeTuple = None
                DID_EPD_INIT = True


            # HIDDEN DARK MODE
            # Himage = ImageMath.eval('255-(a)',a=Himage)
            
            # HIDDEN sunset DARK MODE. if sunsetFlip = True invert display 24 mintues after sunset 
            sunsetFlip = True
            if sunsetFlip:
                sunset_hour, sunset_minute = sunset_time_tuple
                if (sunset_hour < current_hour or current_hour < 2) or (sunset_hour == current_hour and sunset_minute <= current_minute):
                    print("Night Time Dark Mode @ {} {}".format(current_hour, current_minute))
                    Himage = ImageMath.eval('255-(a)', a=Himage)

            if DID_EPD_INIT:
                image_buffer = epd.getbuffer(Himage)
                print("\tDrawing Image to EPD")
                epd.display(image_buffer)

            # Look @ start variable above. find out how long it takes to compute our image
            stop = time()
            time_elapsed = stop - start

            remaining_time = sec_left - time_elapsed
            if remaining_time < 0: remaining_time = 60

            if 5 < current_hour and current_hour < 24:
                # 6:00am - 12:59pm update screen every 3 minutes
                print("\t", round(time_elapsed, 2), "\tseconds per loop\t", "sleeping for {} seconds".format(int(remaining_time) + 120))
                sleep(remaining_time + 120)
            elif current_hour < 2:
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
    # Returns Spotify Token from sp_oauth if token_ifo is stale
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
    """ Returns Spotify Listening Information from Spotify AUTH Token
        Parameters:
            token: Spotify Auth Token generated from OAuth object
        Returns:
            track_name: track name to be displayed
            artist_name: artist name to be displayed
            time_passed: used to calculate time since played, or if currently playing
            context_type: used to determine context icon -> pulled from getContextFromJson()
            context_name: context name to be displayed -> pulled from getContextFromJson()
    """
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
    """ Returns Spotify Context info
        Parameters:
            context_json: json to be parsed
            spotipy_object: used to retreive name of spotify context
        Returns:
            context_type: Either a playlist, artist, or album
            context_name: Context name to be displayed 
    """
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
def getTimeFromDatetime(time_elapsed, oldMinute, twenty_four_clock):
    """ Returns time information from datetime including seconds, time, date, and the current_minute of update
        Parameters:
            time_elapsed: 'jump us forward in time to anticipate compute time'
            oldMinute: used to ensure a proper update interval
            twenty_four_clock: Bool to determine if AM/PM or not
        Returns:
            sec_left: used to know how long we should sleep for before next update on the current_minute
            time_str: time text to be displayed
            date_str: date text to be displayed
            newMinute: will become the oldMinute var in next call for proper interval
    """
    date = dt.now() + timedelta(seconds = time_elapsed) 
    am_pm = date.strftime("%p")
    hour = int(date.strftime("%-H"))
    newMinute = int(date.strftime("%M")[-1])

    # Here we make some considerations so the screen isn't updated too frequently
    # We air on the side of caution, and would rather add an additional current_minute than shrink by a current_minute
    if oldMinute != None and (5 < hour and hour < 24):
        # 6:00am - 11:59pm update screen every 3 mins
        while int(abs(oldMinute - newMinute)) < 3:
            date = dt.now() + timedelta(seconds = time_elapsed)
            newMinute = int(date.strftime("%M")[-1])
            sleep(2)
    # 12:00am - 1:59am update screen every 5 mins at least
    elif oldMinute != None and (hour < 2):
        while int(abs(oldMinute - newMinute)) < 5:
            date = dt.now() + timedelta(seconds = time_elapsed)
            newMinute = int(date.strftime("%M")[-1])
            sleep(2)
    # 2:00am - 5:59am check time every 15ish minutes, granularity here is not paramount
    sec_left = 60 - int(date.strftime("%S")) 
    date_str, am_pm = date.strftime("%a, %b %-d"), date.strftime("%p")

    time_str = date.strftime("%-H:%M") if twenty_four_clock else date.strftime("%-I:%M") + am_pm.lower()
    return sec_left, time_str, date_str, int(newMinute)
def getTimeFromTimeDelta(td):
    """ Determine time since last played in terms of hours and minutes from timedelta"""
    hours, minutes = td.days * 24 + td.seconds // 3600, (td.seconds % 3600) // 60
    return hours, minutes
def getTimeSincePlayed(hours, minutes):
    """ Get str representation of time since last played 
        Parameters:
            hours: int counting hours since last played
            minutes: int counting minutes since last played
        Returns:
            "is listening to" or "# ___ ago" 
    """
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

def getWeather(metric_units):
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
    OW_CITYID = "" # https://openweathermap.org/find? -> find your city id
    OW_OTHER_CITYID = "" 
    URL_UNITS = "&units=metric" if metric_units else "&units=imperial"

    # Get current weather
    OW_CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather?"
    OW_CURRENT_COMPLETE = OW_CURRENT_URL + "appid=" + OW_KEY + "&id=" + OW_CITYID + URL_UNITS
    weather_response = getRequest(OW_CURRENT_COMPLETE)
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
    weather_response = getRequest(OW_CURRENT_COMPLETE)
    weather_json = weather_response.json()
    if weather_json["cod"] != "404":
        other_temp = round(weather_json['main']['feels_like'])

    # Get forecasted weather from feels_like and temp_min, temp_max
    OW_FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast?"
    OW_FORECAST_COMPLETE = OW_FORECAST_URL + "appid=" + OW_KEY + "&id=" + OW_CITYID + URL_UNITS + "&cnt=12"
    weather_response = getRequest(OW_FORECAST_COMPLETE)
    forecast_json = weather_response.json()
    if forecast_json["cod"] != "404":
        for i, l in enumerate(forecast_json['list']):
            i_temp = round(l['main']['feels_like'])
            max_predicted = max(i_temp, round(l['main']['temp_min']))
            min_predicted = min(i_temp, round(l['main']['temp_max']))
            if temp_min > min_predicted: temp_min = min_predicted
            if temp_max < max_predicted: temp_max = max_predicted
    return (temp, temp_max, temp_min, other_temp), (sunset_hour, sunset_minute)

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

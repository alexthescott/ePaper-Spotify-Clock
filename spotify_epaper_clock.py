#!/usr/bin/python
# Some borrowed ideas from SpotifyOAuthDemo.py https://github.com/perelin/spotipy_oauth_demo
# -*- coding:utf-8 -*-

import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging, time, traceback, textwrap, requests, json
import spotipy
import spotipy.util as util
from random import randint
from datetime import timedelta, datetime as dt
from waveshare_epd import epd4in2
from PIL import Image, ImageDraw, ImageFont, ImageMath

def getTimeFromDatetime(TIME_ELAPSED):
    # GET REGULAR TIME
    date = dt.now() + timedelta(seconds = TIME_ELAPSED)
    seconds_left = 60 - int(date.strftime("%S")) 
    date_str, am_pm = date.strftime("%a, %b %d"), date.strftime("%p")
    military_time = date.strftime("%I:%M") + am_pm.lower()
    if military_time[0] == "0": military_time = military_time[1:]
    return seconds_left, military_time, date_str

def getWeather(weather_url_api):
    weather_response = requests.get(OPENWEATHER_COMPLETE_URL)
    weather_json = weather_response.json()
    if weather_json["cod"] != "404":
        weather = weather_json["main"]
        temp = int((weather["temp"] * 9/5) - 459.67)
    return temp

def getSpotipyToken(sp_oauth, token_info):
    token = None
    if token_info:
        print("Found cache token!")
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
    context_type = ""
    context_name = ""
    context_url = ""
    if recent != None and recent['item'] != None:
        # GRAB CURRENT CONTEXT
        context_json = recent['context']
        context_type = context_json['type']
        context_uri = context_json['uri']
        if context_type == 'playlist':
            playlist_json = sp.playlist(context_uri)
            context_name = playlist_json['name']
        elif context_type == 'album':
            album_json = sp.album(context_uri)
            context_name = album_json['name']
        elif context_type == 'artist':
            artist_json = sp.artist(context_uri)
            context_name = artist_json['name']

        track = recent['item']
        track_name, artists = track['name'], track['artists']
        artist_name = ""
        for i in range(len(artists)):
            artist_name += artists[i]['name'] + ", "
        artist_name = artist_name[:-2]
    else:
        # GRAB CURRENT CONTEXT
        recent = sp.current_user_recently_played(1)
        tracks = recent["items"]
        track = tracks[0]
        track_name, artists = track['track']['name'], track['track']['artists']
        artist_name = ""
        for i in range(len(artists)):
            artist_name += track['track']['artists'][i]['name'] + ", "
        artist_name = artist_name[:-2]
    return track_name, artist_name, context_type, context_name

def fixMultilineHyphen(text, width):
    if len(text.split(" ")) == 1 and len(text) > 16:
        lines = textwrap.wrap(text, width = width,  initial_indent = "-")
        temp_lines = []
        for line_count, line in enumerate(lines):
            if len(lines) != line_count+1:
                temp_lines.append(line[1:] + "-")
            else:
                temp_lines.append(str(line))
        return temp_lines
    else:
        return textwrap.wrap(text, width = width)

def drawBoarderLines(image_draw_object):
    # DRAW TWO LINES, SHIFT AROUND
    moveLine = randint(-1, 2)
    image_draw_object.line([(0, 224 + moveLine), (400, 224 + moveLine)], fill = 0) 
    image_draw_object.line([(0, 225 + moveLine), (400, 225 + moveLine)], fill = 0) 
    image_draw_object.line([(0, 226 + moveLine), (400, 226 + moveLine)], fill = 0) 
    image_draw_object.line([(199 + moveLine, 0), (199 + moveLine, 225 + moveLine)], fill = 0) 
    image_draw_object.line([(200 + moveLine, 0), (200 + moveLine, 225 + moveLine)], fill = 0) 
    image_draw_object.line([(201 + moveLine, 0), (201 + moveLine, 225 + moveLine)], fill = 0) 

def drawName(image_draw_object, text, name_x, name_y):
    # DRAW BOLD TEXTNAME @ name_x, name_y
    move_x, move_y = randint(-2, 1), randint(-2, 1)
    name_width, name_height = draw.textsize(text, font = fnt32)
    draw.text((name_x, name_y), text, font = fnt32)
    draw.text((name_x, name_y-1), text, font = fnt32)
    draw.text((name_x-1, name_y-1), text, font = fnt32)
    draw.text((name_x-1, name_y), text, font = fnt32)
    draw.line([(name_x - 1, name_y + name_height + 2), (name_x + name_width - 1, name_y + name_height + 2)], fill = 0)
    draw.line([(name_x - 1, name_y + name_height + 3), (name_x + name_width - 1, name_y + name_height + 3)], fill = 0)

def drawSpotContext(image_draw_object, context_type, context_text, context_x, context_y):
    moveLine = randint(-1, 1)
    if context_type != None:
        context_width, context_height = image_draw_object.textsize(context_text, font = fnt16)
        # STOP OVERFLOW CONTEXT past line
        if context_width + context_x >= moveLine + 200:
            image_draw_object.text((context_x + 22, context_y + 5), context_text[:31] + "...", font = fnt16)
        else:
            image_draw_object.text((context_x + 22, context_y + 5), context_text, font = fnt16)

        # ATTACH ICONS
        if context_type == 'playlist':
            Himage.paste(playlist_icon, (context_x + 1, context_y + 4))
        elif context_type == 'album':
            Himage.paste(album_icon, (context_x - 2, context_y))
        elif context_type == 'artist':
            Himage.paste(artist_icon, (context_x, context_y + 3))

def drawDateTimeTemp(image_draw_object, military_time, date_str, temp):
    temp_x, temp_y = WIDTH - WIDTH // 5, HEIGHT - HEIGHT // 5
    # CHECK for triple digit weather :( and adjust temp print location
    if temp >= 100: temp_x -= 5
    image_draw_object.text((temp_x, temp_y), str(temp) + "F", font = fnt64)

    time_width, time_height = image_draw_object.textsize(military_time, fnt64)
    time_x, time_y = (WIDTH // 40, HEIGHT - (HEIGHT // 5))
    image_draw_object.text((time_x, time_y), military_time, font = fnt64)

    date_width, date_height = image_draw_object.textsize(date_str, fnt32)
    final_date_x = (time_x + time_width)
    date_x, date_y = ((final_date_x + temp_x) // 2) - (date_width // 2), temp_y + date_height // 1.05
    image_draw_object.text((date_x, date_y), date_str, font = fnt32)

def drawTrackText(image_draw_object, track_name, artist_name, track_x, track_y):
    temp_artist_lines = textwrap.wrap(artist_name, width = 17)
    temp_track_lines = textwrap.wrap(track_name, width = 8)
    # IF ARTIST SPACE IS GOING TO BE TINY, PRINT LARGE TRACK TITLES
    if len(temp_artist_lines) <= 2 and len(temp_track_lines) <= 2: 
        # DRAW ALL TRACK TITLES LARGE
        track_lines = fixMultilineHyphen(track_name, 8)
        for track_line_count, line in enumerate(track_lines):
            width, height = image_draw_object.textsize(line, font = fnt64)
            if len(track_lines) == 1:
                image_draw_object.text((track_x, track_y), line, font = fnt64)
                track_line_count = 0.75
            # DRAW NORMALLY
            elif track_line_count < 4:
                image_draw_object.text((track_x, track_y), line, font = fnt64)
                track_y += height
            # BREAK AT 4TH LINE 
            else:
                track_y -= height // 2
                image_draw_object.text((track_x, track_y), "...", font = fnt64)
                return track_line_count, height
    # LARGER ARTIST SPACE, REGULAR RENDER OF TRACK TITLE
    else:
        track_lines = fixMultilineHyphen(track_name, 17)
        # DRAW ALL TRACK TITLES
        for track_line_count, line in enumerate(track_lines):
            width, height = image_draw_object.textsize(line, font = fnt32)
            if track_line_count < 4:
                image_draw_object.text((track_x, track_y), line, font = fnt32)
                track_y += height
            # BREAK AT 5TH LINE 
            else:
                track_y -= height // 2
                image_draw_object.text((track_x, track_y), "...", font = fnt32)
                return track_line_count, height

    return track_line_count, height

def drawArtistText(image_draw_object, track_name, artist_name, track_line_count, track_height, text_x, text_y):
    # IF SPACE FOR LARGE ARTIST TITLE, PRINT IT
    temp_artist_lines = textwrap.wrap(artist_name, width = 8)
    temp_track_lines = textwrap.wrap(track_name, width = 8)
    if len(temp_artist_lines) <= 2 and len(temp_track_lines) == 1:
        width, _ = draw.textsize(artist_name, font = fnt64)
        artist_lines = textwrap.wrap(artist_name, width = 8)
        text_y +=((1 + track_line_count) * track_height) // 1.5
        for artist_line_count, line in enumerate(artist_lines):
            width, height = image_draw_object.textsize(line, fnt64)
            image_draw_object.text((text_x, text_y), line, font = fnt64)
            text_y += height
    else:
        # DRAW ALL ARTIST NAMES
        width, height = draw.textsize(track_name, font = fnt64)
        artist_lines = textwrap.wrap(artist_name, width = 17)

        nudge = 0
        # text_y if two lines of big text
        print("track_height:{} track_line_count:{}".format(track_height, track_line_count))
        if (track_height == 44 or track_height == 48) and track_line_count < 1:
            nudge = track_height * (track_line_count + 1) 
        elif track_height >= 24 and track_height <= 48 and track_line_count < 2:
            nudge = track_height * (track_line_count + 1) * 1.125
        elif track_height >= 22 and track_height <= 48 and track_line_count <= 3:
            nudge = track_height * (track_line_count + 1) * 1.1
        else:
            nudge = track_height * track_line_count
        text_y += nudge

        # fnt32 and fnt16 PRINT
        temp_line = None
        for artist_line_count, line in enumerate(artist_lines):
            # IF WE CAN PRINT A LARGE ARTIST LINE, DO IT
            if A_SPOT_CONTEXT_TYPE == 'artist' or (len(line) <= 17 and len(artist_lines) <= 2):
                width, height = image_draw_object.textsize(line, fnt32)
                image_draw_object.text((text_x, text_y), line, font = fnt32)
                text_y += height
            else:
                # fnt16 PRINT 
                width, height = image_draw_object.textsize(line, fnt16)
                if artist_line_count == 0:
                    temp_line = line
                elif len(artist_lines) % 2 == 1 and len(artist_lines) == artist_line_count + 1 and artist_line_count != 1: 
                    image_draw_object.text((text_x, text_y), line, font = fnt16)
                    text_y += height
                elif artist_line_count % 2 == 0 and len(artist_lines) == artist_line_count + 1:
                    image_draw_object.text((text_x, text_y), temp_line + " " + line, font = fnt16)
                    text_y += height
                elif artist_line_count % 2 == 1:
                    if temp_line == None or len(artist_lines) != artist_line_count + 1:
                        
                        image_draw_object.text((text_x, text_y), temp_line + " " + line, font = fnt16)
                    else:
                        image_draw_object.text((text_x, text_y), line , font = fnt16)
                    text_y += height
                else:
                    temp_line = line
                
            if text_y + height >= 220:
                break

if __name__ == '__main__':
    # Load local resources. Fonts and Icons from /ePaperFonts and /Icons
    fnt32 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 32)
    fnt16 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 16)
    fnt64 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 64)
    playlist_icon = Image.open('Icons/playlist.png')
    artist_icon = Image.open('Icons/artist.png')
    album_icon = Image.open('Icons/album.png')

    # OPEN_WEATHER API SETTUP
    OPENWEATHER_API_KEY = ""
    OPENWEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"
    OPENWEATHER_CITY_ID = ""
    OPENWEATHER_COMPLETE_URL = OPENWEATHER_BASE_URL + "appid=" + OPENWEATHER_API_KEY + "&id=" + OPENWEATHER_CITY_ID + ""

    # UNIVERSAL SPOTIPY VARS 
    SCOPE = "user-read-private, user-read-recently-played, user-read-playback-state, user-read-currently-playing" 
    REDIRECT_URI = 'http://www.google.com/'

    # ALEX SPOTIPY 
    A_SPOT_CLIENT_ID = ''
    A_SPOT_CLIENT_SECRET = ''
    A_SPOT_CONTEXT_TYPE = None
    A_SPOT_CONTEXT_NAME = ""
    A_CACHE = '.a_userauthcache'
    A_USERNAME = ''

    # EMMA SPOTIPY 
    E_SPOT_CLIENT_ID = ''
    E_SPOT_CLIENT_SECRET = ''
    E_SPOT_CONTEXT_TYPE = None
    E_SPOT_CONTEXT_NAME = ""
    E_CACHE = '.e_userauthcache'
    E_USERNAME = ''

    try:
        logging.info("epd4in2 Demo")
        epd = epd4in2.EPD()
        logging.info("init and Clear")
        epd.init()
        epd.Clear()
        WIDTH, HEIGHT = epd.width, epd.height
        TIME_ELAPSED = 11.4

        while True:
            # OPENWEATHER API CALL
            temp = getWeather(OPENWEATHER_COMPLETE_URL)
            print(str(temp) + "F")

            # DEBUG TIMER
            start = time.time()

            # GET REGULAR TIME
            seconds_left, military_time, date_str = getTimeFromDatetime(TIME_ELAPSED)
            print(military_time, date_str)

            # CREATE BLANK IMAGE
            Himage = Image.new('1', (WIDTH, HEIGHT), 128)
            draw = ImageDraw.Draw(Himage)

            # DRAW LINES DATE TIME TEMP ----------------------------------------------------------------
            drawBoarderLines(draw)
            drawDateTimeTemp(draw, military_time, date_str, temp)

            # DRAW NAMES ----------------------------------------------------------------
            alex_x, alex_y = (WIDTH // 50), (HEIGHT // 50)
            drawName(draw, "Alex", alex_x, alex_y)
            emma_x, emma_y = 202 + (WIDTH // 50), (HEIGHT // 50)
            drawName(draw, "Emma", emma_x, emma_y)

            # GET ALEX's SPOTIPY AUTH OBJECT, TOKEN
            alex_sp_oauth = spotipy.oauth2.SpotifyOAuth(A_SPOT_CLIENT_ID, A_SPOT_CLIENT_SECRET, REDIRECT_URI, scope = SCOPE, cache_path = A_CACHE)
            alex_token_info = alex_sp_oauth.get_cached_token()

            alex_token = getSpotipyToken(alex_sp_oauth, alex_token_info)
            if alex_token:
                print("Alex's access token available")
                alex_track_name, alex_artist_name, A_SPOT_CONTEXT_TYPE, A_SPOT_CONTEXT_NAME = getSpotipyInfo(alex_token)
            else:
                print("Alex's access token available")
                alex_track_name, alex_artist_name, A_SPOT_CONTEXT_TYPE, A_SPOT_CONTEXT_NAME = "", "", "", ""

            # ALEX TRACK TITLES CONTEXT ----------------------------------------------------------------
            text_x, text_y = (WIDTH // 50, - (HEIGHT // 1.15) + HEIGHT)
            track_line_count, track_text_size = drawTrackText(draw, alex_track_name, alex_artist_name, text_x, text_y)
            drawArtistText(draw, alex_track_name, alex_artist_name, track_line_count, track_text_size, text_x, text_y)
            alex_context_x, alex_context_y = WIDTH // 100, 195
            drawSpotContext(draw, A_SPOT_CONTEXT_TYPE, A_SPOT_CONTEXT_NAME, alex_context_x, alex_context_y)

            # GET EMMAS's SPOTIFY TOKEN
            emma_sp_oauth = spotipy.oauth2.SpotifyOAuth(E_SPOT_CLIENT_ID, E_SPOT_CLIENT_SECRET, REDIRECT_URI, scope = SCOPE, cache_path = E_CACHE)
            emma_token_info = emma_sp_oauth.get_cached_token()
            emma_token = getSpotipyToken(emma_sp_oauth, emma_token_info)
            if emma_token:
                print("Emma's access token available")
                emma_track_name, emma_artist_name, E_SPOT_CONTEXT_TYPE, E_SPOT_CONTEXT_NAME = getSpotipyInfo(emma_token)
                print(emma_track_name, emma_artist_name)
            else:
                print(":( Emma's access token unavailable")
                emma_track_name, emma_artist_name, E_SPOT_CONTEXT_TYPE, E_SPOT_CONTEXT_NAME = "", "", "", ""            

            # EMMA TRACK TITLES ----------------------------------------------------------------
            text_x, text_y = (WIDTH // 50 + 200, - (HEIGHT // 1.15) + HEIGHT)
            track_line_count, track_text_size = drawTrackText(draw, emma_track_name, emma_artist_name, text_x, text_y)
            drawArtistText(draw, emma_track_name, emma_artist_name, track_line_count, track_text_size, text_x, text_y)
            emma_context_x, emma_context_y = 202 + WIDTH // 100, 195 
            drawSpotContext(draw, E_SPOT_CONTEXT_TYPE, E_SPOT_CONTEXT_NAME, emma_context_x, emma_context_y)
            # HIDDEN DARK MODE
            # Himage = ImageMath.eval('255-(a)',a=Himage)
            epd.display(epd.getbuffer(Himage))

            # DEBUG TIMER 
            stop = time.time() 
            TIME_ELAPSED = stop - start
            remaining_time = seconds_left - TIME_ELAPSED
            print(round(TIME_ELAPSED, 2), "seconds per loop")
            print(int(remaining_time), "seconds until refresh")
            if remaining_time > 0:
                time.sleep(remaining_time)

    except Exception as e:
        print(e)
        epd4in2.epdconfig.module_exit()
        exit()

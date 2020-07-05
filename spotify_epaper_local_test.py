import textwrap, requests, json
import spotipy
import spotipy.util as util
from PIL import Image, ImageDraw, ImageFont, ImageMath
from random import randint
from datetime import timedelta, datetime as dt

def getTimeFromDatetime():
    date = dt.now()
    print("\t" + date.strftime("%M"))
    seconds_left = 60 - int(date.strftime("%S")) 
    date_str, am_pm = date.strftime("%a, %b %-d"), date.strftime("%p")
    time_str = date.strftime("%-I:%M") + am_pm.lower()
    return seconds_left, time_str, date_str

def getTimeFromTimeDelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    # seconds = (seconds % 60) 
    return hours, minutes

def getTimeSincePlayed(hours, minutes):
    if hours == 0 and minutes <=4:
        return " is listening to"
    elif hours == 0:
        return str(round_down(minutes, 5)) + " minutes ago"
    elif hours == 1:
        return str(hours) + " hour ago"
    elif hours < 24:
        return str(hours) + " hours ago"
    elif 24 <= hours and hours > 24:
        return str(hours // 24) + " day ago"
    else:
        return str(hours // 24) + " days ago"

def getWeather(weather_url_api):
    weather_response = requests.get(weather_url_api)
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

def getSpotipyInfo(token):
    # GRAB CURRENT OR RECENT TRACK OBJECT
    sp = spotipy.Spotify(auth=token)
    recent = sp.current_user_playing_track()
    context_type = ""
    context_name = ""
    time_passed = ""
    if recent != None and recent['item'] != None:
        # GRAB CONTEXT
        context_json = recent['context']
        context_type, context_name = getContextFromJson(context_json, sp)

        # GET Track && artist
        track = recent['item']
        track_name, artists = track['name'], track['artists']
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
        artist_name = ""
        for i in range(len(artists)):
            artist_name += track['track']['artists'][i]['name'] + ", "
        artist_name = artist_name[:-2]

        str_timestamp = track['played_at']

        current_dt = dt.utcnow()
        str_timestamp = str_timestamp[:10] + " " + str_timestamp[11:19]
        timestamp = dt.strptime(str_timestamp, "%Y-%m-%d %H:%M:%S")
        time_passed = current_dt - timestamp
        hours_passed, minutes_passed = getTimeFromTimeDelta(time_passed)
        time_passed = getTimeSincePlayed(hours_passed, minutes_passed)

        context_json = track['context']
        context_type, context_name = getContextFromJson(context_json, sp)

    return track_name, artist_name, time_passed, context_type, context_name 

def drawBoarderLines(image_draw_object):
    image_draw_object.line([(0, 224), (400, 224)], fill = 0) 
    image_draw_object.line([(0, 225), (400, 225)], fill = 0) 
    image_draw_object.line([(0, 226), (400, 226)], fill = 0) 
    image_draw_object.line([(199, 0), (199, 225)], fill = 0) 
    image_draw_object.line([(200, 0), (200, 225)], fill = 0) 
    image_draw_object.line([(201, 0), (201, 225)], fill = 0) 

def drawName(image_draw_object, text, name_x, name_y):
    # DRAW BOLD TEXTNAME @ name_x, name_y
    move_x, move_y = randint(-2, 1), randint(-2, 1)
    name_width, name_height = draw.textsize(text, font = helveti32)
    draw.text((name_x, name_y), text, font = helveti32)
    # draw.line([(name_x - 1, name_y + name_height + 2), (name_x + name_width - 1, name_y + name_height + 2)], fill = 0)
    draw.line([(name_x - 1, name_y + name_height + 3), (name_x + name_width - 1, name_y + name_height + 3)], fill = 0)

    return name_width, name_height

def drawUserTimeAgo(image_draw_object, text, time_x, time_y):
    move_x, move_y = randint(-2, 1), randint(-2, 1)
    time_width, time_height = draw.textsize(text, font = DSfnt16)
    draw.text((time_x, time_y), text, font = DSfnt16)

def drawSpotContext(image_draw_object, context_type, context_text, context_x, context_y):
    moveLine = randint(-1, 1)
    if context_type != None:
        context_width, context_height = image_draw_object.textsize(context_text, font = DSfnt16)
        # STOP OVERFLOW left panel 
        if context_x < 10 and context_width + context_x >= moveLine + 200:
            image_draw_object.text((context_x + 22, context_y + 5), context_text[:31] + "...", font = DSfnt16)     	
        # STOP OVERFLOW right panel 
        elif context_x > 200 and context_width + context_x >= moveLine + 400:
            image_draw_object.text((context_x + 22, context_y + 5), context_text[:31] + "...", font = DSfnt16)
        else:
            image_draw_object.text((context_x + 22, context_y + 5), context_text, font = DSfnt16)

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
    image_draw_object.text((temp_x, temp_y), str(temp) + "F", font = DSfnt64)

    time_width, time_height = image_draw_object.textsize(military_time, DSfnt64)
    time_x, time_y = (WIDTH // 40, HEIGHT - (HEIGHT // 5))
    image_draw_object.text((time_x, time_y), military_time, font = DSfnt64)

    date_width, date_height = image_draw_object.textsize(date_str, DSfnt32)
    final_date_x = (time_x + time_width)
    date_x, date_y = ((final_date_x + temp_x) // 2) - (date_width // 2), temp_y + date_height // 1.05
    image_draw_object.text((date_x, date_y), date_str, font = DSfnt32)

def drawTrackText(image_draw_object, track_name, artist_name, track_x, track_y):
    temp_artist_lines = textwrap.wrap(artist_name, width = 17)
    temp_track_lines = textwrap.wrap(track_name, width = 8)
    track_width, track_height = image_draw_object.textsize(track_name, font = DSfnt32)
    artist_width, artist_height = image_draw_object.textsize(artist_name, font = DSfnt32)

    # IF ARTIST SPACE IS GOING TO BE TINY, PRINT LARGE TRACK TITLES
    if len(temp_artist_lines) <= 3 and len(temp_track_lines) <= 2 or track_width < 190: 
        # DRAW ALL TRACK TITLES LARGE
        track_lines = fixMultilineHyphen(track_name, 8)
        for track_line_count, line in enumerate(track_lines):
            width, height = image_draw_object.textsize(line, font = DSfnt64)
            if len(track_lines) == 1:
                image_draw_object.text((track_x, track_y), line, font = DSfnt64)
                track_line_count = 0.75
            # DRAW NORMALLY
            elif track_line_count < 4:
                image_draw_object.text((track_x, track_y), line, font = DSfnt64)
                track_y += height
            # BREAK AT 4TH LINE 
            else:
                track_y -= height // 2
                image_draw_object.text((track_x, track_y), "...", font = DSfnt64)
                return track_line_count, height
    # LARGER ARTIST SPACE, REGULAR RENDER OF TRACK TITLE
    else:
        track_lines = fixMultilineHyphen(track_name, 17)
        # DRAW ALL TRACK TITLES
        for track_line_count, line in enumerate(track_lines):
            width, height = image_draw_object.textsize(line, font = DSfnt32)
            if track_line_count < 4:
                image_draw_object.text((track_x, track_y), line, font = DSfnt32)
                track_y += height
            # BREAK AT 5TH LINE 
            else:
                track_y -= height // 2
                image_draw_object.text((track_x, track_y), "...", font = DSfnt32)
                return track_line_count, height

    return track_line_count, height

def drawArtistText(image_draw_object, track_name, artist_name, track_line_count, track_height, text_x, text_y):
    # IF SPACE FOR LARGE ARTIST TITLE, PRINT IT
    temp_artist_lines = fixMultilineHyphen(artist_name, 8)
    temp_track_lines = textwrap.wrap(track_name, width = 8)
    if len(temp_artist_lines) <= 2 and len(temp_track_lines) == 1:
        width, _ = draw.textsize(artist_name, font = DSfnt64)
        artist_lines = temp_artist_lines
        text_y +=((1 + track_line_count) * track_height) // 1.5
        for artist_line_count, line in enumerate(artist_lines):
            width, height = image_draw_object.textsize(line, DSfnt64)
            image_draw_object.text((text_x, text_y), line, font = DSfnt64)
            text_y += height
    else:
        # DRAW ALL ARTIST NAMES
        width, height = draw.textsize(track_name, font = DSfnt64)
        artist_lines = fixMultilineHyphen(artist_name, 17)


        nudge = 0
        # text_y if two lines of big text
        print("track_height:{} track_line_count:{}".format(track_height, track_line_count))
        if (track_height == 44 or track_height == 48) and track_line_count < 1:
            nudge = track_height * (track_line_count + 1) // 1.1
        elif (track_height >= 22 or track_height <= 48) and track_line_count < 2:
            nudge = track_height * (track_line_count + 1) * 1.125
        elif (track_height >= 22 or track_height <= 48) and track_line_count <= 3:
            nudge = track_height * (track_line_count + 1) * 1.05
        elif track_line_count >= 4:
            nudge = track_height * (track_line_count + 1)
        else:
            nudge = track_height * (track_line_count + 1)
        text_y += nudge

        # DSfnt32 and DSfnt16 PRINT
        temp_line = None
        for artist_line_count, line in enumerate(artist_lines):
            # IF WE CAN PRINT A LARGE ARTIST LINE, DO IT
            if A_SPOT_CONTEXT_TYPE == 'artist' or (len(line) <= 17 and len(artist_lines) <= 2):
                width, height = image_draw_object.textsize(line, DSfnt32)
                image_draw_object.text((text_x, text_y), line, font = DSfnt32)
                text_y += height
            else:
                # DSfnt16 PRINT 
                width, height = image_draw_object.textsize(line, DSfnt16)
                if artist_line_count == 0:
                    temp_line = line
                elif len(artist_lines) % 2 == 1 and len(artist_lines) == artist_line_count + 1 and artist_line_count != 1: 
                    image_draw_object.text((text_x, text_y), line, font = DSfnt16)
                    text_y += height
                elif artist_line_count % 2 == 0 and len(artist_lines) == artist_line_count + 1:
                    image_draw_object.text((text_x, text_y), temp_line + " " + line, font = DSfnt16)
                    text_y += height
                elif artist_line_count % 2 == 1:
                    if temp_line == None or len(artist_lines) != artist_line_count + 1:
                        
                        image_draw_object.text((text_x, text_y), temp_line + " " + line, font = DSfnt16)
                    else:
                        image_draw_object.text((text_x, text_y), line , font = DSfnt16)
                    text_y += height
                else:
                    temp_line = line
                
            if text_y + height >= 220:
                break

def fixMultilineHyphen(text, width):
    if len(text.split(" ")) == 1 and len(text) > width:
        lines = textwrap.wrap(text, width = width - 1,  initial_indent = "-")
        temp_lines = []
        for line_count, line in enumerate(lines):
            if len(lines) != line_count+1:
                temp_lines.append(line[1:] + "-")
            else:
                temp_lines.append(str(line))
        return temp_lines
    else:
        return textwrap.wrap(text, width = width)

def round_down(num, divisor):
    return num - (num%divisor)

if __name__ == '__main__':
    # Load local resources. Fonts and Icons from /ePaperFonts and /Icons
    DSfnt16 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 16)
    DSfnt32 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 32)
    DSfnt64 = ImageFont.truetype('ePaperFonts/Nintendo-DS-BIOS.ttf', 64)

    helveti16 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 16)
    helveti32 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 32)
    helveti64 = ImageFont.truetype('ePaperFonts/Habbo.ttf', 64)

    playlist_icon = Image.open('Icons/playlist.png')
    artist_icon = Image.open('Icons/artist.png')
    album_icon = Image.open('Icons/album.png')

    # OPEN_WEATHER API SETTUP
    OPENWEATHER_API_KEY = ""
    OPENWEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"
    OPENWEATHER_CITY_ID = "" # https://openweathermap.org/find
    OPENWEATHER_COMPLETE_URL = OPENWEATHER_BASE_URL + "appid=" + OPENWEATHER_API_KEY + "&id=" + OPENWEATHER_CITY_ID + ""

    # UNIVERSAL SPOTIPY 
    SCOPE = "user-read-recently-played, user-read-playback-state, user-read-currently-playing" 
    REDIRECT_URI = 'http://www.google.com/'

    # ALEX SPOTIPY 
    A_SPOT_CLIENT_ID = ''
    A_SPOT_CLIENT_SECRET = ''
    A_SPOT_CONTEXT_TYPE = None
    A_SPOT_CONTEXT_NAME = ""
    A_CACHE = ''
    A_USERNAME = ''

    # EMMA SPOTIPY 
    E_SPOT_CLIENT_ID = ''
    E_SPOT_CLIENT_SECRET = ''
    E_SPOT_CONTEXT_TYPE = None
    E_SPOT_CONTEXT_NAME = ""
    E_CACHE = ''
    E_USERNAME = ''

    WIDTH, HEIGHT = 400, 300

    # OPENWEATHER API CALL
    temp = getWeather(OPENWEATHER_COMPLETE_URL)
    # print(str(temp) + "F")

    seconds_left, military_time, date_str = getTimeFromDatetime()
    print(military_time)

    # CREATE BLANK IMAGE
    Himage = Image.new('1', (WIDTH, HEIGHT), 128)
    draw = ImageDraw.Draw(Himage)

    # DRAW LINES DATE TIME TEMP ----------------------------------------------------------------
    drawBoarderLines(draw)
    drawDateTimeTemp(draw, military_time, date_str, temp)

    # GET ALEX's SPOTIPY AUTH OBJECT ----------------------------------------------------------------
    alex_sp_oauth = spotipy.oauth2.SpotifyOAuth(A_SPOT_CLIENT_ID, A_SPOT_CLIENT_SECRET, REDIRECT_URI, scope = SCOPE, cache_path = A_CACHE, requests_timeout = 10)
    alex_token_info = alex_sp_oauth.get_cached_token()

    # GET ALEX's SPOTIFY TOKEN
    alex_token = getSpotipyToken(alex_sp_oauth, alex_token_info)
    if alex_token:
        print("Alex's access token available")
        alex_track_name, alex_artist_name, alex_time_passed, A_SPOT_CONTEXT_TYPE, A_SPOT_CONTEXT_NAME = getSpotipyInfo(alex_token)
    else:
        print(":( Alex's access token unavailable")
        alex_track_name, alex_artist_name = "", ""

    # ALEX TRACK TITLES CONTEXT 
    text_x, text_y = (WIDTH // 50, - (HEIGHT // 1.125) + HEIGHT)
    track_line_count, track_text_size = drawTrackText(draw, alex_track_name, alex_artist_name, text_x, text_y)
    drawArtistText(draw, alex_track_name, alex_artist_name, track_line_count, track_text_size, text_x, text_y)
    alex_context_x, alex_context_y = WIDTH // 100, 195
    drawSpotContext(draw, A_SPOT_CONTEXT_TYPE, A_SPOT_CONTEXT_NAME, alex_context_x, alex_context_y)

    # GET EMMA's SPOTIPY AUTH OBJECT ----------------------------------------------------------------
    emma_sp_oauth = spotipy.oauth2.SpotifyOAuth(E_SPOT_CLIENT_ID, E_SPOT_CLIENT_SECRET, REDIRECT_URI, scope = SCOPE, cache_path = E_CACHE, requests_timeout = 10)
    emma_token_info = emma_sp_oauth.get_cached_token()

    # GET EMMAS's SPOTIFY TOKEN
    emma_token = getSpotipyToken(emma_sp_oauth, emma_token_info)
    if emma_token:
        print("Emma's access token available")
        emma_track_name, emma_artist_name, emma_time_passed, E_SPOT_CONTEXT_TYPE, E_SPOT_CONTEXT_NAME = getSpotipyInfo(emma_token)
        print(emma_track_name, emma_artist_name)
    else:
        print(":( Emma's access token unavailable")
        emma_track_name, emma_artist_name, emma_time_passed, E_SPOT_CONTEXT_TYPE, E_SPOT_CONTEXT_NAME = "", "", "", ""

    # EMMA TRACK TITLES 
    text_x, text_y = (WIDTH // 50 + 203, - (HEIGHT // 1.125) + HEIGHT)
    track_line_count, track_text_size = drawTrackText(draw, emma_track_name, emma_artist_name, text_x, text_y)
    drawArtistText(draw, emma_track_name, emma_artist_name, track_line_count, track_text_size, text_x, text_y)
    emma_context_x, emma_context_y = 202 + WIDTH // 100, 195 
    drawSpotContext(draw, E_SPOT_CONTEXT_TYPE, E_SPOT_CONTEXT_NAME, emma_context_x, emma_context_y)

    # NAMES ----------------------------------------------------------------
    alex_x, alex_y = (WIDTH // 50), (HEIGHT // 50)
    alex_width, alex_height = drawName(draw, "Alex", alex_x, alex_y)
    drawUserTimeAgo(draw, alex_time_passed, alex_x + 10 + alex_width, alex_y + alex_height // 2)
    emma_x, emma_y = 202 + (WIDTH // 50), (HEIGHT // 50)
    emma_width, emma_height = drawName(draw, "Emma", emma_x, emma_y)
    drawUserTimeAgo(draw, emma_time_passed, emma_x + 10 + emma_width, emma_y + emma_height // 2)

    # HIDDEN DARK MODE 
    # Himage = ImageMath.eval('255-(a)',a=Himage)
    Himage.show()
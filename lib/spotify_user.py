import spotipy
from spotipy.exceptions import SpotifyException
from requests.exceptions import ReadTimeout
import json
import logging
from datetime import timedelta, datetime as dt
from lib.clock_logging import logger

spotify_logger = logging.getLogger('spotipy.client')

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

class SpotifyUser():
    def __init__(self, name="CHANGE_ME", single_user=False, main=True):
        # Generate Spotify client_id and client_secret
        # https://developer.spotify.com/dashboard/
        self.scope = "user-read-private, user-read-recently-played, user-read-playback-state, user-read-currently-playing"
        self.redirect_uri = 'http://www.google.com/'
        
        
        self.spot_client_id = '7423e2b31f244d2498126f51075aba54'  
        self.spot_client_secret = 'de3a403cc1e7445896a80f7a8f18d8c8' 
        self.cache = 'cache/.authcache1' if main else 'cache/.authcache2'
        self.name = name # drawn at the top of the screen
        self.SINGLE_USER = single_user
        self.oauth = None
        self.oauth_token_info = None
        self.sp = None
        self.load_credentials()
        self.update_spotipy_token()

    def load_credentials(self):
        with open('config/keys.json', 'r') as f:
            credentials = json.load(f)
            self.spot_client_id = credentials['spot_client_id']
            self.spot_client_secret = credentials['spot_client_secret']

    def get_user_token(self):

        # GET right user's SPOTIFY TOKEN
        # print("Get right user's Spotify Token")
        response = self.update_spotipy_token(self.oauth, self.oauth_token_info)
        if response:
            track, artist, time_since, tmp_ctx_type, tmp_ctx_name, track_image_link, album_name = self.get_spotipy_info(self.token, get_album_art=self.SINGLE_USER)
            ctx_type = tmp_ctx_type if tmp_ctx_type != "" else ctx_type
            ctx_name = tmp_ctx_name if tmp_ctx_name != "" else ctx_name
        else:
            print(":( Right's access token unavailable")
            r_track, r_artist = "", ""

    # Spotify Functions
    def update_spotipy_token(self):
        """ Updates Spotify Token from self.oauth if token_info is stale. """
        self.oauth = spotipy.oauth2.SpotifyOAuth(self.spot_client_id, self.spot_client_secret, self.redirect_uri, scope=self.scope, cache_path=self.cache, requests_timeout=10)
        self.oauth_token_info = self.oauth.get_cached_token()

        token = None
        if self.oauth_token_info:
            token = self.oauth_token_info['access_token']
        else:
            auth_url = self.oauth.get_authorize_url()
            print(auth_url)
            response = input("Paste the above link into your browser, then paste the redirect url here: ")
            code = self.oauth.parse_response_code(response)
            if code:
                print("Found Spotify auth code in Request URL! Trying to get valid access token...")
                token_info = self.oauth.get_access_token(code)
                token = token_info['access_token']
        self.token = token
        self.sp = spotipy.Spotify(auth=self.token)
        return True
    
    def get_spotipy_info(self):
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
        self.dt = dt.now()
        for _ in range(3):
            try:
                recent = self.sp.current_user_playing_track()
                break
            except (SpotifyException, ReadTimeout) as e:
                logger.info(e)
                self.update_spotipy_token()
        else:
            logger.error(f"Failed to get current {self.name}'s Spotify Info")
            return "", "", "", "", "", None, None
        
        context_type, context_name, time_passed = "", "", ""
        track_image_link, album_name = None, None  # used if single_user
        if recent is not None and recent['item'] is not None:
            # GET CURRENT CONTEXT
            context_type, context_name = self.get_context_from_json(recent['context'])
            time_passed = " is listening to"

            # GET TRACK && ARTIST
            track_name, artists = recent['item']['name'], recent['item']['artists']
            artist_name = ""
            for i in range(len(artists)):
                artist_name += artists[i]['name'] + ", "
            artist_name = artist_name[:-2]

            # need image data as single_user
            if self.SINGLE_USER:
                track_image_link = recent['item']['album']['images'][0]['url']
                album_name = recent['item']['album']['name']
        else:
            # GRAB OLD CONTEXT
            recent = self.sp.current_user_recently_played(1)
            tracks = recent["items"]
            track = tracks[0]
            track_name, artists = track['track']['name'], track['track']['artists']
            track_image_link = tracks[0]['track']['album']['images'][0]['url']
            album_name = track['track']['album']['name']
            # Concatenate artist names
            artist_name = ""
            for i in range(len(artists)):
                artist_name += track['track']['artists'][i]['name'] + ", "
            artist_name = artist_name[:-2]

            last_timestamp = track['played_at']
            str_timestamp = last_timestamp[:10] + " " + last_timestamp[11:19]
            timestamp = dt.strptime(str_timestamp, "%Y-%m-%d %H:%M:%S")
            hours_passed, minutes_passed = get_time_from_timedelta(dt.utcnow() - timestamp)
            time_passed = get_time_since_played(hours_passed, minutes_passed)
            context_type, context_name = self.get_context_from_json(track['context'])
        logger.info(f"Spotify Info:{track_name} by {artist_name} playing from from {context_name} {context_type}")
        return track_name, artist_name, time_passed, context_type, context_name, track_image_link, album_name
        
    def get_context_from_json(self, context_json):
        """ Return Spotify Context info.

            Parameters:
                context_json: json to be parsed
            Return:
                context_type: Either a playlist, artist, or album
                context_name: Context name to be displayed
        """
        # Ignore Spotify logger for get_context_from_json
        spotify_logger.disabled = True
        context_type, context_name = "", ""
        if context_json is not None:
            context_type = context_json['type']
            context_uri = context_json['uri']
            if context_type == 'playlist':
                try:
                    playlist_json = self.sp.playlist(context_uri)
                    context_name = playlist_json['name']
                except SpotifyException:
                    logger.info("playlist() call failed, assuming User is listening to DJ mix")
                    context_name = "DJ"
            elif context_type == 'album':
                album_json = self.sp.album(context_uri)
                context_name = album_json['name']
            elif context_type == 'artist':
                artist_json = self.sp.artist(context_uri)
                context_name = artist_json['name']
        spotify_logger.disabled = False
        return context_type, context_name
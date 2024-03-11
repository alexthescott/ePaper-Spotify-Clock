import json
import logging
from datetime import datetime, timedelta

import spotipy
from requests.exceptions import ReadTimeout
from spotipy.exceptions import SpotifyException

from lib.clock_logging import logger
from lib.json_io import LocalJsonIO
spotify_logger = logging.getLogger('spotipy.client')


def get_time_from_timedelta(td: timedelta):
    """ 
    Determine time since last played in terms of hours and minutes from timedelta. 
    """
    hours, minutes = td.days * 24 + td.seconds // 3600, (td.seconds % 3600) // 60
    return hours, minutes

def get_time_since_played(hours: int, minutes: int):
    """ 
    Get str representation of time since last played.
    Args:
        hours (int): hours since last played
        minutes (int): minutes since last played
    Returns:
        "is listening to" or "# ___ ago"
    """
    if hours == 0:
        return "is listening to" if minutes <= 4 else f"{minutes - (minutes % 5)} minutes ago"
    elif hours < 24:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = hours // 24
        return f"{days} day{'s' if days > 1 else ''} ago"

class SpotifyUser():
    """ 
    Class to handle Spotify User Information needed for Clock()
    """
    def __init__(self, name: str = "CHANGE_ME", single_user: bool = False, main_user: bool = True):
        # Generate Spotify client_id and client_secret
        # https://developer.spotify.com/dashboard/
        self.scope = "user-read-private, user-read-recently-played, user-read-playback-state, user-read-currently-playing"
        self.redirect_uri = 'http://www.google.com/'
        self.single_user = single_user
        self.main_user = main_user
        self.spot_client_id = ''  
        self.spot_client_secret = '' 
        self.cache = 'cache/.authcache1' if self.main_user else 'cache/.authcache2'
        self.name = name # drawn at the top of the screen
        self.oauth = None
        self.oauth_token_info = None
        self.sp = None
        self.dt = None
        self.ctx_io = LocalJsonIO()
        self.album_art_right_side = None
        self.right_side = (self.single_user and self.album_art_right_side) or not self.single_user and not self.main_user
        logger.info("User: %s Right Side: %s", self.name, self.right_side)
        self.load_credentials()
        self.load_display_settings()
        self.update_spotipy_token()

    def load_credentials(self):
        """
        Load display settings from config/display_settings.json
        """
        with open('config/keys.json', 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            self.spot_client_id = credentials['spot_client_id_me'] if self.main_user else credentials['spot_client_id_you']
            self.spot_client_secret = credentials['spot_client_secret_me'] if self.main_user else credentials['spot_client_secret_you']

    def load_display_settings(self):
        """
        Load display settings from config/display_settings.json
        """
        with open("config/display_settings.json", encoding="utf-8") as display_settings:
            display_settings = json.load(display_settings)
            single_user_settings = display_settings["single_user_settings"]
            self.album_art_right_side = single_user_settings["album_art_right_side"]

    # Spotify Functions
    def update_spotipy_token(self):
        """ 
        Updates Spotify Token from self.oauth if token_info is stale. 
        """
        self.oauth = spotipy.oauth2.SpotifyOAuth(self.spot_client_id, self.spot_client_secret, self.redirect_uri, scope=self.scope, cache_path=self.cache, requests_timeout=10)
        try:
            self.oauth_token_info = self.oauth.get_cached_token()
        except ConnectionError:
            logger.error("Failed to update cached_token(): ConnectionError")
            return False

        if self.oauth_token_info:
            self.token = self.oauth_token_info['access_token']
        else:
            auth_url = self.oauth.get_authorize_url()
            print(auth_url)
            response = input("Paste the above link into your browser, then paste the redirect url here: ")
            code = self.oauth.parse_response_code(response)
            if code:
                print("Found Spotify auth code in Request URL! Trying to get valid access token...")
                token_info = self.oauth.get_access_token(code)
                self.token = token_info['access_token']
        self.sp = spotipy.Spotify(auth=self.token)
        return True

    def get_spotipy_info(self):
        """ 
        Return Spotify Listening Information from Spotify AUTH Token.
        Args:
            token: Spotify Auth Token generated from OAuth object
        Return:
            track_name: track name to be displayed
            artist_name: artist name to be displayed
            time_passed: used to calculate time since played, or if currently playing
            context_type: used to determine context icon -> pulled from get_context_from_json()
            context_name: context name to be displayed -> pulled from get_context_from_json()
        """
        if not self.sp:
            logger.error("%s's SpotipyObject Never Created", self.name)
            return "Not Available", "Failed to get Spotify Data", "", "Failed", "Failed", None, "Failed"
        self.dt = datetime.now()
        for _ in range(3):
            try:
                recent = self.sp.current_user_playing_track()
                break
            except (SpotifyException, ReadTimeout) as e:
                logger.error(e)
                self.update_spotipy_token()
            except ConnectionError as e:
                logger.error(e)
                old_context = self.ctx_io.read_json_ctx(self.right_side)
                return self.get_stored_json_info(old_context)
        else:
            logger.error("Failed to get current %s's Spotify Info", self.name)
            old_context = self.ctx_io.read_json_ctx(self.right_side)
            return self.get_stored_json_info(old_context)

        context_type, context_name, time_passed = "", "", ""
        # used if single_user
        track_image_link, album_name = None, None
        # if user is currently playing a song, get current context, track and artist, store into json
        if recent and recent['item']:
            context_type, context_name = self.get_context_from_json(recent)
            time_passed = " is listening to"
            track_name, artists = recent['item']['name'], recent['item']['artists']
            artist_name = ', '.join(artist['name'] for artist in artists)

            if self.single_user:
                track_image_link = recent['item']['album']['images'][0]['url']
                album_name = recent['item']['album']['name']
            else:
                track_image_link = None
                album_name = None
            
            current_info = {
                "unix_timestamp": recent["timestamp"],
                "context_type": context_type, 
                "context_name": context_name, 
                "time_passed": time_passed, 
                "track_name": track_name, 
                "artist_name": artist_name, 
                "track_image_link": track_image_link, 
                "album_name": album_name
            }
            self.ctx_io.write_json_ctx(current_info, self.right_side)
        else:
            # get recently played info if user is not currently playing a song
            # only use that info if it's newer than stored json info
            recent = self.sp.current_user_recently_played(1)
            unix_timestamp = int(recent['cursors']['after'])
            old_context = self.ctx_io.read_json_ctx(self.right_side)
            if old_context and 'unix_timestamp' in old_context and old_context['unix_timestamp'] > unix_timestamp:
                return self.get_stored_json_info(old_context)
            
            tracks = recent["items"]
            track = tracks[0]
            track_name, artists = track['track']['name'], track['track']['artists']
            track_image_link = tracks[0]['track']['album']['images'][0]['url']
            album_name = track['track']['album']['name']
            # Concatenate all artist names
            artist_name = ', '.join(track['track']['artists'][i]['name'] for i in range(len(artists)))
            last_timestamp = track['played_at']
            timestamp = datetime.strptime(last_timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
            hours_passed, minutes_passed = get_time_from_timedelta(self.dt.utcnow() - timestamp)
            time_passed = get_time_since_played(hours_passed, minutes_passed)
            context_type, context_name = self.get_context_from_json(track)
        logger.info("%s: %s, %s by %s playing from from %s %s",self.name, time_passed, track_name, artist_name, context_name, context_type)
        return track_name, artist_name, time_passed, context_type, context_name, track_image_link, album_name
        
    def get_context_from_json(self, track_json: dict):
        """ 
        Return Spotify Context info.
        Args:
            context_json: json to be parsed
        Return:
            context_type: Either a playlist, artist, or album
            context_name: Context name to be displayed
        """
        context_type, context_name = "", ""
        context_json = track_json['context']
        if context_json:
            context_type = context_json['type']
            context_uri = context_json['uri']
        else:
            context_type = "album"
            track_info = track_json['track'] if 'track' in track_json else track_json['item']
            context_uri = track_info['album']['uri']
        
        context_fetchers = {
            'playlist': self.sp.playlist,
            'album': self.sp.album,
            'artist': self.sp.artist
        }
        
        fetcher = context_fetchers.get(context_type, None)
        
        if fetcher:
            # Ignore Spotify logger for get_context_from_json
            spotify_logger.disabled = True
            try:
                context_name = fetcher(context_uri)['name']
            except SpotifyException:
                # playlist() call failed, assuming User is listening to DJ mix
                if context_type == 'playlist':
                    context_name = "DJ"
        elif context_type == 'collection':
            context_name = "Liked Songs"
            
        spotify_logger.disabled = False
        return context_type, context_name
    
    def get_stored_json_info(self, context_json: dict):
        """
        Retrieves information from a stored JSON context.
        Args:
            context_json (dict): The JSON context containing the stored information.
        Returns:
            tuple: A tuple containing the following information:
                - track_name (str): The name of the track.
                - artist_name (str): The name of the artist.
                - time_passed (str): The time passed since the track was played.
                - context_type (str): The type of context.
                - context_name (str): The name of the context.
                - track_image_link (str): The link to the track's image.
                - album_name (str): The name of the album.
        """
        logger.info("Using stored context for %s", self.name)
        if not context_json:
            return "Not Available", "Failed to get Spotify Data", "", "Failed", "Failed", None, "Failed"
        track_name = context_json['track_name']
        artist_name = context_json['artist_name']
        context_type = context_json['context_type']
        context_name = context_json['context_name']
        track_image_link = context_json['track_image_link']
        album_name = context_json['album_name']
        dt_object = datetime.utcfromtimestamp(context_json['unix_timestamp'] / 1000)
        dt_object_str = dt_object.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        timestamp = datetime.strptime(dt_object_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        hours_passed, minutes_passed = get_time_from_timedelta(self.dt.utcnow() - timestamp)
        time_passed = get_time_since_played(hours_passed, minutes_passed)
        return track_name, artist_name, time_passed, context_type, context_name, track_image_link, album_name

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

import requests
from requests.exceptions import ReadTimeout
import spotipy
from spotipy.exceptions import SpotifyException

from lib.clock_logging import logger
from lib.display_settings import display_settings
from lib.json_io import LocalJsonIO

spotify_logger = logging.getLogger('spotipy.client')


def get_time_from_timedelta(td: timedelta) -> Tuple[int, int]:
    """ 
    Determine time since last played in terms of hours and minutes from timedelta. 

    Args:
        td (timedelta): The timedelta object.

    Returns:
        Tuple[int, int]: The hours and minutes since last played.
    """
    hours = td.days * 24 + td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    return hours, minutes

def get_time_since_played(hours: int, minutes: int) -> str:
    """ 
    Get str representation of time since last played.

    Args:
        hours (int): hours since last played
        minutes (int): minutes since last played

    Returns:
        str: "is listening to" or "# ___ ago"
    """
    if hours == 0:
        return "is listening to" if minutes <= 4 else f"{minutes - (minutes % 5)} minutes ago"
    elif hours < 24:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = hours // 24
        return f"{days} day{'s' if days > 1 else ''} ago"

class SpotifyUser:
    """ 
    Class to handle Spotify User Information needed for Clock()
    """
    def __init__(self, name: str = "CHANGE_ME", single_user: bool = False, main_user: bool = True):
        self.ds = display_settings
        self.scope = "user-read-private, user-read-recently-played, user-read-playback-state, user-read-currently-playing"
        self.redirect_uri = 'http://www.google.com/'
        self.single_user = single_user
        self.main_user = main_user
        self.spot_client_id = ''
        self.spot_client_secret = ''
        self.cache = 'cache/.authcache1' if self.main_user else 'cache/.authcache2'
        self.name = name
        self.oauth = None
        self.oauth_token_info = None
        self.sp = None
        self.dt = None
        self.ctx_io = LocalJsonIO()
        self.right_side = (self.single_user and self.ds.album_art_right_side) or not self.single_user and not self.main_user
        logger.info("User: %s Right Side: %s", self.name, self.right_side)
        self.load_credentials()
        self.update_spotipy_token()

    def load_credentials(self):
        """
        Load display settings from config/display_settings.json
        """
        with open('config/keys.json', 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            self.spot_client_id = credentials['spot_client_id_me'] if self.main_user else credentials['spot_client_id_you']
            self.spot_client_secret = credentials['spot_client_secret_me'] if self.main_user else credentials['spot_client_secret_you']

    def update_spotipy_token(self):
        """ 
        Updates Spotify Token from self.oauth if token_info is stale. 
        """
        self.oauth = spotipy.oauth2.SpotifyOAuth(self.spot_client_id, self.spot_client_secret, self.redirect_uri, scope=self.scope, cache_path=self.cache, requests_timeout=10)
        try:
            self.oauth_token_info = self.oauth.get_cached_token()
        except requests.exceptions.ConnectionError:
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
        logger.info("%s's Spotify access_token granted", self.name)
        return True

    def get_spotipy_info(self) -> Tuple[str, str, str, str, str, Optional[str], str]:
        """ 
        Return Spotify Listening Information from Spotify AUTH Token.

        Returns:
            Tuple[str, str, str, str, str, Optional[str], str]: 
                track_name: track name to be displayed
                artist_name: artist name to be displayed
                time_passed: used to calculate time since played, or if currently playing
                context_type: used to determine context icon -> pulled from get_context_from_json()
                context_name: context name to be displayed -> pulled from get_context_from_json()
                track_image_link: link to the track image
                album_name: name of the album
        """
        if not self.sp:
            logger.error("%s's SpotipyObject Never Created", self.name)
            return "Not Available", "Failed to get Spotify Data", "", "Failed", "Failed", None, "Failed"
        self.dt = datetime.now()
        recent = self.get_recent_track()
        if recent is None:
            old_context = self.ctx_io.read_json_ctx(self.right_side)
            return self.get_stored_json_info(old_context)

        if recent and recent['item']:
            return self.get_currently_playing_info(recent)
        else:
            return self.get_recently_played_info()

    def get_recent_track(self) -> Optional[Dict[str, Any]]:
        """
        Tries to get the currently playing track for the user.
        If it fails due to a SpotifyException or ReadTimeout, it tries to update the Spotify token and retry.
        If it fails due to a ConnectionError, it logs the error and returns None.
        If it fails after 3 attempts, it logs an error message and returns None.

        Returns:
            Optional[Dict[str, Any]]: The currently playing track for the user, or None if it fails to get it.
        """
        for _ in range(3):
            try:
                return self.sp.current_user_playing_track()
            except (SpotifyException, ReadTimeout) as e:
                logger.error(e)
                self.update_spotipy_token()
            except requests.exceptions.ConnectionError as e:
                logger.error(e)
                return None
        logger.error("Failed to get current %s's Spotify Info", self.name)
        return None

    def get_currently_playing_info(self, recent: Dict[str, Any]) -> Tuple[str, str, str, str, str, Optional[str], str]:
        """
        Extracts the currently playing information from the given recent track data.

        Args:
            recent (Dict[str, Any]): The recent track data.

        Returns:
            Tuple[str, str, str, str, str, Optional[str], str]: 
                track_name: track name to be displayed
                artist_name: artist name to be displayed
                time_passed: used to calculate time since played, or if currently playing
                context_type: used to determine context icon
                context_name: context name to be displayed
                track_image_link: link to the track image
                album_name: name of the album
        """
        context_type, context_name = self.get_context_from_json(recent)
        time_passed = " is listening to"
        track_name, artists = recent['item']['name'], recent['item']['artists']
        artist_name = ', '.join(artist['name'] for artist in artists)
        track_image_link, album_name = self.get_track_image_and_album(recent)
        current_info = self.create_current_info(recent["timestamp"], context_type, context_name, time_passed, track_name, artist_name, track_image_link, album_name)
        self.ctx_io.write_json_ctx(current_info, self.right_side)
        logger.info("%s: %s, %s by %s playing from from %s %s", self.name, time_passed, track_name, artist_name, context_name, context_type)
        return track_name, artist_name, time_passed, context_type, context_name, track_image_link, album_name

    def get_track_image_and_album(self, recent: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts the track image URL and album name from the given recent track data.

        Args:
            recent (Dict[str, Any]): The recent track data.

        Returns:
            Tuple[Optional[str], Optional[str]]: 
                track_image_link: link to the track image, or None if not a single user
                album_name: name of the album, or None if not a single user
        """
        if self.single_user:
            return recent['item']['album']['images'][0]['url'], recent['item']['album']['name']
        return None, None

    def create_current_info(self, unix_timestamp: int, context_type: str, context_name: str, time_passed: str, track_name: str, artist_name: str, track_image_link: Optional[str], album_name: Optional[str]) -> Dict[str, Union[int, str, Optional[str]]]:
        """
        Creates a dictionary with the currently playing information.

        Args:
            unix_timestamp (int): The timestamp of the track.
            context_type (str): The type of the context.
            context_name (str): The name of the context.
            time_passed (str): The time passed since the track started playing.
            track_name (str): The name of the track.
            artist_name (str): The name of the artist.
            track_image_link (Optional[str]): The link to the track image.
            album_name (Optional[str]): The name of the album.

        Returns:
            Dict[str, Union[int, str, Optional[str]]]: A dictionary with the currently playing information.
        """
        return {
            "unix_timestamp": unix_timestamp,
            "context_type": context_type, 
            "context_name": context_name, 
            "time_passed": time_passed, 
            "track_name": track_name, 
            "artist_name": artist_name, 
            "track_image_link": track_image_link, 
            "album_name": album_name
        }

    def get_recently_played_info(self) -> Optional[Dict[str, Any]]:
        """
        Gets the recently played track information for the user.
        If the track is not found or the stored timestamp is newer, it returns the stored information.
        Otherwise, it returns the track information from the recent track data.

        Returns:
            Optional[Dict[str, Any]]: The recently played track information, or None if it fails to get it.
        """
        recent = self.get_recently_played_track()
        if recent is None:
            return None

        unix_timestamp = int(recent['cursors']['after'])
        old_context = self.ctx_io.read_json_ctx(self.right_side)

        if old_context and 'unix_timestamp' in old_context and old_context['unix_timestamp'] > unix_timestamp:
            return self.get_stored_json_info(old_context)

        return self.get_track_info_from_recent(recent, unix_timestamp)

    def get_recently_played_track(self) -> Optional[Dict[str, Any]]:
        """
        Tries to get the most recently played track for the user.
        If it fails due to a SpotifyException with an expired access token, it tries to update the Spotify token and retry.
        If it fails due to a SpotifyException with a different reason, it raises the exception.

        Returns:
            Optional[Dict[str, Any]]: The most recently played track for the user, or None if it fails to get it.
        """
        try:
            return self.sp.current_user_recently_played(1)
        except SpotifyException as e:
            if 'The access token expired' in str(e):
                self.update_spotipy_token()
                return self.sp.current_user_recently_played(1)
            raise

    def get_track_info_from_recent(self, recent: Dict[str, Any], unix_timestamp: int) -> Tuple[str, str, str, str, str, str, str]:
        """
        Extracts the track information from the given recent track data.

        Args:
            recent (Dict[str, Any]): The recent track data.
            unix_timestamp (int): The timestamp of the track.

        Returns:
            Tuple[str, str, str, str, str, str, str]: 
                track_name: track name to be displayed
                artist_name: artist name to be displayed
                time_passed: used to calculate time since played, or if currently playing
                context_type: used to determine context icon
                context_name: context name to be displayed
                track_image_link: link to the track image
                album_name: name of the album
        """
        tracks = recent["items"]
        track = tracks[0]
        track_name, artists = track['track']['name'], track['track']['artists']
        track_image_link = track['track']['album']['images'][0]['url']
        album_name = track['track']['album']['name']
        artist_name = ', '.join(artist['name'] for artist in artists)
        last_timestamp = track['played_at']
        timestamp = datetime.strptime(last_timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        hours_passed, minutes_passed = get_time_from_timedelta(self.dt.utcnow() - timestamp)
        time_passed = get_time_since_played(hours_passed, minutes_passed)
        context_type, context_name = self.get_context_from_json(track)
        current_info = self.create_current_info(unix_timestamp, context_type, context_name, time_passed, track_name, artist_name, track_image_link, album_name)
        self.ctx_io.write_json_ctx(current_info, self.right_side)
        logger.info("%s: %s, %s by %s playing from from %s %s", self.name, time_passed, track_name, artist_name, context_name, context_type)
        return track_name, artist_name, time_passed, context_type, context_name, track_image_link, album_name

    def get_context_from_json(self, track_json: Dict[str, Any]) -> Tuple[str, str]:
        """
        Returns Spotify Context info.

        Args:
            track_json (Dict[str, Any]): The track data to be parsed.

        Returns:
            Tuple[str, str]: 
                context_type: Either a playlist, artist, or album.
                context_name: Context name to be displayed.
        """
        context_type, context_name = "", ""
        context_json = track_json.get('context')

        if context_json:
            context_type = context_json['type']
            context_uri = context_json['uri']
        else:
            context_type = "album"
            track_info = track_json.get('track') or track_json.get('item')
            context_uri = track_info['album']['uri']

        context_fetchers = {
            'playlist': self.sp.playlist,
            'album': self.sp.album,
            'artist': self.sp.artist
        }

        fetcher = context_fetchers.get(context_type)

        if fetcher:
            spotify_logger.disabled = True
            try:
                context_name = fetcher(context_uri)['name']
            except SpotifyException:
                if context_type == 'playlist':
                    context_name = "DJ"
        elif context_type == 'collection':
            context_name = "Liked Songs"

        spotify_logger.disabled = False
        return context_type, context_name

    def get_stored_json_info(self, context_json: Dict[str, Any]) -> Tuple[str, str, str, str, str, Optional[str], str]:
        """
        Retrieves information from a stored JSON context.

        Args:
            context_json (Dict[str, Any]): The JSON context containing the stored information.

        Returns:
            Tuple[str, str, str, str, str, Optional[str], str]: 
                track_name: The name of the track.
                artist_name: The name of the artist.
                time_passed: The time passed since the track was played.
                context_type: The type of context.
                context_name: The name of the context.
                track_image_link: The link to the track's image.
                album_name: The name of the album.
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

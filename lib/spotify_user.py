import functools
import json
import logging
import random
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

import requests
from requests.exceptions import ReadTimeout
import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError

from lib.clock_logging import logger
from lib.display_settings import display_settings
from lib.json_io import LocalJsonIO

spotify_logger = logging.getLogger('spotipy.client')

# Sentinel distinguishing "the API call itself failed" from a legitimate
# `None` response (e.g. current_user_playing_track() returns None when
# nothing is currently playing, which is not a failure).
_FETCH_FAILED = object()


def _retry_with_backoff(
    exceptions: Tuple[type, ...],
    attempts: int = 3,
    base: float = 1.0,
    cap: float = 16.0,
):
    """
    Retry decorator with exponential backoff and jitter.

    Honors `Retry-After` on 429s, backs off on 5xx, re-raises other 4xx immediately.
    Catches network-level errors listed in `exceptions` (e.g., ReadTimeout, ConnectionError).
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last = None
            for i in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except SpotifyException as e:
                    last = e
                    if e.http_status == 429:
                        retry_after = (e.headers or {}).get('Retry-After')
                        wait = float(retry_after) if retry_after else base * (2 ** i)
                    elif 500 <= (e.http_status or 0) < 600:
                        wait = min(cap, base * (2 ** i)) + random.uniform(0, 1)
                    else:
                        raise
                except exceptions as e:
                    last = e
                    wait = min(cap, base * (2 ** i)) + random.uniform(0, 1)
                if i < attempts - 1:
                    logger.warning("retrying %s after %.1fs (%s)", fn.__name__, wait, type(last).__name__)
                    time.sleep(wait)
            raise last
        return wrapper
    return deco


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
        self.scope = "user-read-private user-read-recently-played user-read-playback-state user-read-currently-playing"
        self.redirect_uri = 'http://127.0.0.1:8080/callback'
        self.single_user = single_user
        self.main_user = main_user
        self.spot_client_id = ''
        self.spot_client_secret = ''
        self.cache = 'cache/.authcache1' if self.main_user else 'cache/.authcache2'
        self.name = name
        self.oauth = None
        self.oauth_token_info = None
        self.token = None
        self.token_expires_at: Optional[float] = None
        self.sp = None
        self.dt = None
        self.ctx_io = LocalJsonIO()
        self.right_side = (self.single_user and self.ds.album_art_right_side) or not self.single_user and not self.main_user
        logger.info("User: %s Right Side: %s", self.name, self.right_side)
        self.load_credentials()
        if not self.update_spotipy_token():
            logger.error("Spotify token init failed for %s — will retry in tick loop", self.name)

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

        Retries with exponential backoff on transient OAuth/network errors. Returns
        True if a usable Spotify client is available afterward, False otherwise.
        """
        self.oauth = spotipy.oauth2.SpotifyOAuth(
            client_id=self.spot_client_id,
            client_secret=self.spot_client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            cache_handler=spotipy.CacheFileHandler(cache_path=self.cache),
            requests_timeout=10,
            open_browser=False,
        )

        self.oauth_token_info = None
        for attempt in range(3):
            try:
                self.oauth_token_info = self.oauth.get_cached_token()
                break
            except requests.exceptions.HTTPError as e:
                if e.response is not None and 400 <= e.response.status_code < 500:
                    logger.error("OAuth 4xx — credentials likely invalid: %s", e)
                    return False
                wait = min(16.0, 2.0 ** attempt) + random.uniform(0, 1)
                logger.warning("OAuth HTTPError %s — retrying in %.1fs", e, wait)
                time.sleep(wait)
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout, SpotifyOauthError) as e:
                wait = min(16.0, 2.0 ** attempt) + random.uniform(0, 1)
                logger.warning("OAuth %s — retrying in %.1fs", type(e).__name__, wait)
                time.sleep(wait)
        else:
            logger.error("OAuth failed after 3 attempts for %s", self.name)
            return False

        if self.oauth_token_info:
            self.token = self.oauth_token_info['access_token']
            self.token_expires_at = self.oauth_token_info.get('expires_at')
        elif sys.stdin.isatty():
            auth_url = self.oauth.get_authorize_url()
            print(auth_url)
            response = input("Paste the above link into your browser, then paste the redirect url here: ")
            code = self.oauth.parse_response_code(response)
            if code:
                print("Found Spotify auth code in Request URL! Trying to get valid access token...")
                token_info = self.oauth.get_access_token(code)
                self.token = token_info['access_token']
                self.token_expires_at = token_info.get('expires_at')
        else:
            logger.error("No cached Spotify token for %s and no TTY for interactive auth", self.name)
            return False

        if not self.token:
            return False

        self.sp = spotipy.Spotify(auth_manager=self.oauth, requests_timeout=10, retries=0)
        logger.info("%s's Spotify access_token granted", self.name)
        return True

    def _ensure_fresh_token(self) -> None:
        """Refresh token proactively when within 2 minutes of expiry."""
        if self.token_expires_at and time.time() < self.token_expires_at - 120:
            return
        self.update_spotipy_token()

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
        if recent is _FETCH_FAILED:
            old_context = self.ctx_io.read_json_ctx(self.right_side)
            return self.get_stored_json_info(old_context)

        if recent and recent['item']:
            return self.get_currently_playing_info(recent)
        else:
            # Nothing currently playing — fall back to play history rather
            # than stale stored context.
            return self.get_recently_played_info()

    @_retry_with_backoff((ReadTimeout, requests.exceptions.ConnectionError))
    def _fetch_current_user_playing_track(self) -> Optional[Dict[str, Any]]:
        return self.sp.current_user_playing_track()

    def get_recent_track(self) -> Optional[Dict[str, Any]]:
        """
        Tries to get the currently playing track for the user.

        Proactively refreshes the token if it's near expiry. On 401, refreshes once and
        retries. Network errors and transient 5xx are handled by the retry decorator.

        Returns None if nothing is currently playing (a legitimate Spotify API
        response) — caller falls back to recently-played history. Returns the
        _FETCH_FAILED sentinel if the API call itself could not be completed —
        caller falls back to stale stored context instead.
        """
        if not self.sp:
            return _FETCH_FAILED
        self._ensure_fresh_token()
        spotify_logger.disabled = True
        try:
            return self._fetch_current_user_playing_track()
        except SpotifyException as e:
            if e.http_status == 401:
                self.update_spotipy_token()
                try:
                    return self._fetch_current_user_playing_track()
                except Exception as inner:
                    logger.error("Retry after 401 failed for %s: %s", self.name, inner)
                    return _FETCH_FAILED
            logger.error("SpotifyException for %s: %s", self.name, e)
            return _FETCH_FAILED
        except Exception as e:
            logger.error("Failed to get current track for %s: %s", self.name, e)
            return _FETCH_FAILED
        finally:
            spotify_logger.disabled = False

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

    def get_recently_played_info(self) -> Tuple[str, str, str, str, str, Optional[str], str]:
        """
        Gets the recently played track information for the user.
        If the track is not found or the stored timestamp is newer, it returns the stored information.
        Otherwise, it returns the track information from the recent track data.

        Returns:
            Tuple[str, str, str, str, str, Optional[str], str]: The recently played track
                information, or the stale stored context if the API call failed.
        """
        recent = self.get_recently_played_track()
        if recent is None:
            return self.get_stored_json_info(self.ctx_io.read_json_ctx(self.right_side))

        cursors = recent.get('cursors') or {}
        after = cursors.get('after')
        if after is None:
            logger.info("No 'cursors.after' for %s — using stored context", self.name)
            return self.get_stored_json_info(self.ctx_io.read_json_ctx(self.right_side))
        unix_timestamp = int(after)
        old_context = self.ctx_io.read_json_ctx(self.right_side)

        if old_context and 'unix_timestamp' in old_context and old_context['unix_timestamp'] > unix_timestamp:
            return self.get_stored_json_info(old_context)

        return self.get_track_info_from_recent(recent, unix_timestamp)

    @_retry_with_backoff((ReadTimeout, requests.exceptions.ConnectionError))
    def _fetch_recently_played(self) -> Optional[Dict[str, Any]]:
        return self.sp.current_user_recently_played(1)

    def get_recently_played_track(self) -> Optional[Dict[str, Any]]:
        """
        Tries to get the most recently played track for the user.

        On any 401, refreshes the token once and retries. Network errors and 5xx are
        absorbed by the retry decorator. Returns None on unrecoverable failure so the
        caller can fall back to stored context instead of crashing the loop.
        """
        if not self.sp:
            return None
        self._ensure_fresh_token()
        spotify_logger.disabled = True
        try:
            return self._fetch_recently_played()
        except SpotifyException as e:
            if e.http_status == 401:
                self.update_spotipy_token()
                try:
                    return self._fetch_recently_played()
                except Exception as inner:
                    logger.error("Retry after 401 failed for %s: %s", self.name, inner)
                    return None
            logger.error("SpotifyException for %s: %s", self.name, e)
            return None
        except Exception as e:
            logger.error("Failed to get recently played for %s: %s", self.name, e)
            return None
        finally:
            spotify_logger.disabled = False

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
        tracks = recent.get("items") or []
        if not tracks:
            logger.info("No recently played items for %s — using stored context", self.name)
            return self.get_stored_json_info(self.ctx_io.read_json_ctx(self.right_side))
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
            except (ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning("Context fetch for %s timed out: %s", context_type, type(e).__name__)
            finally:
                spotify_logger.disabled = False
        elif context_type == 'collection':
            context_name = "Liked Songs"

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

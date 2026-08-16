"""
Loopback-only HTTP server for re-authorizing Spotify once a refresh token
expires (Spotify caps refresh tokens at 180 days from original authorization
— see REFRESH_TOKEN_LIFETIME_DAYS in lib/spotify_user.py). Run this on the
Pi; since it only binds to 127.0.0.1, reach it from another machine with an
SSH tunnel:

    ssh -L 8080:localhost:8080 <pi-user>@<pi-host>

then, with the tunnel open, run this script on the Pi and open the printed
link in a browser on the machine you tunneled from. See the README's
"Re-authorizing Spotify" section for the full walkthrough.
"""
import argparse
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from lib.clock_logging import logger
from lib.display_settings import display_settings
from lib.spotify_user import SpotifyUser

TIMEOUT_SECONDS = 10 * 60


def _make_handler(spotify_user: SpotifyUser, auth_url: str, done: threading.Event, result: dict):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # keep stdout clean; real logging goes through `logger`

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == '/callback':
                params = parse_qs(parsed.query)
                if 'error' in params:
                    self._respond(400, f"Spotify returned an error: {params['error'][0]}")
                    result['ok'] = False
                    done.set()
                    return
                code = params.get('code', [None])[0]
                if not code:
                    self._respond(400, "No authorization code in callback URL.")
                    return
                ok = spotify_user.complete_reauth(code)
                if ok:
                    self._respond(200, "Spotify re-authorization complete. You can close this tab.")
                else:
                    self._respond(500, "Re-authorization failed — check cache/clock.log.")
                result['ok'] = ok
                done.set()
            else:
                self._respond(200, f'<a href="{auth_url}">Click here to re-authorize Spotify</a>')

        def _respond(self, status: int, body: str) -> None:
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"<html><body style='font-family:sans-serif'>{body}</body></html>".encode('utf-8'))

    return Handler


def run_reauth(main_user: bool = True, name: str = 'Spotify User') -> bool:
    """
    Starts the loopback callback server, prints the link to open, and blocks
    until re-authorization completes (or TIMEOUT_SECONDS elapses).
    """
    spotify_user = SpotifyUser(name=name, single_user=True, main_user=main_user)
    if not spotify_user.oauth:
        logger.error("Could not build a Spotify OAuth manager for %s — check config/keys.json", name)
        return False
    auth_url = spotify_user.oauth.get_authorize_url()

    parsed_redirect = urlparse(spotify_user.redirect_uri)
    host, port = parsed_redirect.hostname, parsed_redirect.port

    done = threading.Event()
    result: dict = {}
    handler = _make_handler(spotify_user, auth_url, done, result)
    server = HTTPServer((host, port), handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"\nRe-authorizing '{name}'. Open this link in a browser on the machine you SSH-tunneled from:\n")
    print(f"  http://{host}:{port}/\n")
    print(f"Waiting up to {TIMEOUT_SECONDS // 60} minutes...\n")

    done.wait(timeout=TIMEOUT_SECONDS)
    server.shutdown()
    server_thread.join()

    if not done.is_set():
        logger.error("Re-authorization timed out after %d minutes for %s", TIMEOUT_SECONDS // 60, name)
        print("Timed out waiting for re-authorization.")
        return False

    ok = result.get('ok', False)
    print("Done." if ok else "Re-authorization failed — check cache/clock.log.")
    return ok


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Re-authorize the clock's Spotify account after its refresh token expires."
    )
    parser.add_argument(
        '--secondary', action='store_true',
        help="Re-authorize the second user (config's *_you keys) instead of the main one",
    )
    parsed_args = parser.parse_args()

    if parsed_args.secondary:
        ok = run_reauth(main_user=False, name=display_settings.name_2)
    else:
        ok = run_reauth(main_user=True, name=display_settings.name_1)

    sys.exit(0 if ok else 1)

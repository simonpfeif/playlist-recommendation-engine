import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import requests
from dotenv import load_dotenv
import json


load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

SCOPES = "user-top-read user-read-recently-played"

auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = parse_qs(urlparse(self.path).query)
        auth_code = query.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Success! You can close this tab.</h1>")
    
    def log_message(self, format, *args):
        pass

def main():
    # Step 1: Open browser to Spotify login
    auth_url = "https://accounts.spotify.com/authorize?" + urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES
    })

    print("Opening Spotify login in your browser...")
    webbrowser.open(auth_url)

    # Step 2: User (me) logs in and approves
    # Step 3: Spotify API redirects user to callback url

    # Step 4: Catch the redirect with the auth code
    server = HTTPServer(("127.0.0.1", 3000), CallbackHandler)
    server.handle_request()

    if not auth_code:
        print("No auth code received")
        return
    
    # Step 5: Exchange code for tokens
    response = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    })

    tokens = response.json()

    # Save tokens locally for future use
    with open("spotify_tokens.json", "w") as f:
        json.dump(tokens, f, indent=2)

    print("Tokens saved to spotify_tokens.json")

if __name__ == "__main__":
    main()
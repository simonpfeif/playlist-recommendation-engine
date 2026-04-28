import json
import os
import urllib.request
import urllib.parse

def get_access_token():
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": os.environ["SPOTIFY_REFRESH_TOKEN"],
        "client_id": os.environ["SPOTIFY_CLIENT_ID"],
        "client_secret": os.environ["SPOTIFY_CLIENT_SECRET"]
    }).encode()

    req = urllib.request.Request("https://accounts.spotify.com/api/token", data=data)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]

def lambda_handler(event, context):
    token = get_access_token()

    req = urllib.request.Request(
        "https://api.spotify.com/v1/me/top/tracks?limit=10&time_range=short_term",
        headers={"Authorization": f"Bearer {token}"}
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    tracks = [
        {
            "name": t["name"],
            "artist": t["artists"][0]["name"],
            "album": t["album"]["name"]
        }
        for t in data["items"]
    ]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(tracks, indent=2)
    }
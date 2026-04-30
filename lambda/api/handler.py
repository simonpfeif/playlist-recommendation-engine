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

def spotify_get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def lambda_handler(event, context):
    token = get_access_token()

    # Top tracks across three time ranges
    top_short = spotify_get(
        "https://api.spotify.com/v1/me/top/tracks?limit=50&time_range=short_term",
        token
    )
    top_medium = spotify_get(
        "https://api.spotify.com/v1/me/top/tracks?limit=50&time_range=medium_term",
        token
    )

    # Recently played with timestamps
    recent = spotify_get(
        "https://api.spotify.com/v1/me/player/recently-played?limit=50",
        token
    )

    # Top artists for genre data
    artists = spotify_get(
        "https://api.spotify.com/v1/me/top/artists?limit=50&time_range=medium_term",
        token
    )

    def extract_tracks(items):
        return [
            {
                "id": t["id"],
                "name": t["name"],
                "artist": t["artists"][0]["name"],
                "artist_id": t["artists"][0]["id"],
                "album": t["album"]["name"],
                "popularity": t["popularity"],
                "duration_ms": t["duration_ms"]
            }
            for t in items
        ]

    # Build recently played frequency + time patterns
    recent_data = []
    for item in recent["items"]:
        recent_data.append({
            "track_id": item["track"]["id"],
            "track_name": item["track"]["name"],
            "artist": item["track"]["artists"][0]["name"],
            "played_at": item["played_at"],
            "popularity": item["track"]["popularity"]
        })

    # Extract genre map from top artists
    genre_map = [
        {
            "artist": a["name"],
            "genres": a["genres"],
            "popularity": a["popularity"]
        }
        for a in artists["items"]
    ]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "top_tracks_short_term": extract_tracks(top_short["items"]),
            "top_tracks_medium_term": extract_tracks(top_medium["items"]),
            "recently_played": recent_data,
            "genre_map": genre_map
        }, indent=2)
    }
"""Check which Spotify Web API endpoints this app can still use after the 2026 restrictions.

Usage:
    python scripts/verify_spotify.py           # read-only checks
    python scripts/verify_spotify.py --write   # also creates a private test playlist

Reads credentials from .env and the refresh token from spotify_tokens.json.
"""
import json
import os
import sys
import urllib.parse

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.spotify.com/v1"


def get_access_token():
    with open("spotify_tokens.json") as f:
        refresh_token = json.load(f)["refresh_token"]
    resp = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": os.environ["SPOTIFY_CLIENT_ID"],
        "client_secret": os.environ["SPOTIFY_CLIENT_SECRET"]
    })
    resp.raise_for_status()
    body = resp.json()
    print(f"Token scopes: {body.get('scope')}\n")
    return body["access_token"]


def call(method, path, token, body=None):
    url = path if path.startswith("http") else API + path
    resp = requests.request(method, url, json=body, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json() if resp.content else {}


def check(name, fn):
    try:
        detail = fn()
        print(f"PASS  {name}: {detail}")
        return True
    except requests.HTTPError as e:
        print(f"FAIL  {name}: HTTP {e.response.status_code} {e.response.text[:200]}")
    except Exception as e:
        print(f"FAIL  {name}: {type(e).__name__}: {e}")
    return False


def main():
    write = "--write" in sys.argv
    token = get_access_token()
    state = {}

    def liked_songs():
        page1 = call("GET", "/me/tracks?limit=50", token)
        page2 = call("GET", page1["next"], token) if page1.get("next") else {"items": []}
        return f"total={page1['total']}, page1={len(page1['items'])}, page2={len(page2['items'])}"

    def my_playlists():
        me = call("GET", "/me", token)
        resp = call("GET", "/me/playlists?limit=50", token)
        owned = [p for p in resp["items"] if p and p["owner"]["id"] == me["id"]]
        state["owned_playlist"] = owned[0]["id"] if owned else None
        return f"total={resp['total']}, owned on first page={len(owned)}"

    def playlist_items():
        if not state.get("owned_playlist"):
            return "skipped (no owned playlist)"
        resp = call("GET", f"/playlists/{state['owned_playlist']}/items?limit=50", token)
        return f"total={resp['total']}, returned={len(resp['items'])}"

    def top_long_term():
        resp = call("GET", "/me/top/tracks?limit=50&time_range=long_term", token)
        return f"returned={len(resp['items'])}"

    def search():
        q = urllib.parse.quote('track:"Blame Brett" artist:"The Beaches"')
        resp = call("GET", f"/search?q={q}&type=track&limit=10", token)
        items = resp["tracks"]["items"]
        top = items[0]
        state["test_uri"] = top["uri"]
        state["artist_id"] = top["artists"][0]["id"]
        return (f"results={len(items)}, top='{top['name']}' by {top['artists'][0]['name']}, "
                f"isrc={top.get('external_ids', {}).get('isrc')}, popularity={top.get('popularity')}")

    def single_artist():
        a = call("GET", f"/artists/{state['artist_id']}", token)
        return f"genres={a.get('genres')}, popularity={a.get('popularity')}"

    def create_playlist():
        p = call("POST", "/me/playlists", token,
                 {"name": "API test (safe to delete)", "public": False})
        call("POST", f"/playlists/{p['id']}/items", token, {"uris": [state["test_uri"]]})
        return f"created playlist {p['external_urls']['spotify']} with 1 track"

    check("Liked Songs (paginated)", liked_songs)
    check("List my playlists", my_playlists)
    check("Read items of an owned playlist", playlist_items)
    check("Top tracks long_term", top_long_term)
    if check("Search track (limit 10)", search):
        check("Get single artist", single_artist)
        if write:
            check("Create playlist + add items", create_playlist)
        else:
            print("SKIP  Create playlist + add items (pass --write)")


if __name__ == "__main__":
    main()

"""Check the Last.fm endpoints the recommender will use.

Usage:
    python scripts/verify_lastfm.py ["Artist Name" "Track Name"]

Needs LAST_FM_API_KEY in .env (create one at https://www.last.fm/api/account/create).
"""
import os
import sys
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://ws.audioscrobbler.com/2.0/"


def lastfm(method, **params):
    resp = requests.get(API, headers={"User-Agent": "playlist-recommendation-engine"}, params={
        "method": method,
        "api_key": os.environ["LAST_FM_API_KEY"],
        "format": "json",
        **params
    })
    body = resp.json()
    if "error" in body:
        raise RuntimeError(f"Last.fm error {body['error']}: {body['message']}")
    return body


def main():
    artist, track = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("The Beaches", "Blame Brett")

    info = lastfm("artist.getInfo", artist=artist)["artist"]
    print(f"artist.getInfo     {info['name']}: listeners={info['stats']['listeners']}, "
          f"tags={[t['name'] for t in info['tags']['tag']]}")

    similar = lastfm("artist.getSimilar", artist=artist, limit=10)["similarartists"]["artist"]
    print(f"artist.getSimilar  {[(a['name'], round(float(a['match']), 2)) for a in similar]}")

    if similar:
        top = lastfm("artist.getTopTracks", artist=similar[0]["name"], limit=5)["toptracks"]["track"]
        print(f"artist.getTopTracks ({similar[0]['name']})  {[t['name'] for t in top]}")

    sim_tracks = lastfm("track.getSimilar", artist=artist, track=track, limit=10)["similartracks"]["track"]
    print(f"track.getSimilar   {[(t['name'], t['artist']['name']) for t in sim_tracks]}")

    user = os.environ.get("LAST_FM_USERNAME")
    if not user:
        print("\nSKIP  user history checks (set LAST_FM_USERNAME in .env)")
        return

    print()
    info = lastfm("user.getInfo", user=user)["user"]
    print(f"user.getInfo       playcount={info['playcount']}, "
          f"registered={datetime.fromtimestamp(int(info['registered']['unixtime']), timezone.utc):%Y-%m-%d}")

    # With limit=1, the last page holds the oldest scrobble
    recent = lastfm("user.getRecentTracks", user=user, limit=1)["recenttracks"]
    oldest_page = recent["@attr"]["totalPages"]
    oldest = lastfm("user.getRecentTracks", user=user, limit=1, page=oldest_page)["recenttracks"]["track"]
    # The now-playing track (no "date") is included on every page, so skip it
    oldest = [t for t in (oldest if isinstance(oldest, list) else [oldest]) if "date" in t][-1]
    print(f"oldest scrobble    {oldest['date']['#text']}: {oldest['name']} by {oldest['artist']['#text']}")

    latest = lastfm("user.getRecentTracks", user=user, limit=5)["recenttracks"]["track"]
    print("latest scrobbles   " + ", ".join(
        f"{t['name']} by {t['artist']['#text']} ({t['date']['#text'] if 'date' in t else 'now playing'})"
        for t in latest))

    top = lastfm("user.getTopArtists", user=user, period="3month", limit=10)["topartists"]["artist"]
    print(f"top artists (3mo)  {[(a['name'], int(a['playcount'])) for a in top]}")

    loved = lastfm("user.getLovedTracks", user=user, limit=1)["lovedtracks"]["@attr"]["total"]
    print(f"loved tracks       {loved}")


if __name__ == "__main__":
    main()

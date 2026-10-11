# Playlist Recommendation Engine

A better version of Spotify's DJ: every week, build a playlist of **10 songs you haven't heard but probably will love**, based on what listeners with similar taste are playing.

> **Status:** early development. See [PLAN.md](PLAN.md) for the roadmap, current phase, and decision log.

## How it works (v1)

```
Spotify API ──► Ingest ──► DynamoDB ──► Recommend ──► Spotify playlist
 (your plays,    Lambda    (plays,       Lambda        (10 songs, written
  likes, tops)             heard set,      │            to your account)
                           taste profile)  │
                                           ▼
                                  Last.fm API (similar artists/tracks,
                                  crowd-sourced from millions of listeners)
```

1. **Ingest:** read your recent plays, top tracks and artists, Liked Songs, and playlists from Spotify, and store them in DynamoDB.
2. **Profile:** build a taste profile from *recent* listening, with older plays counting less over time. Keep a separate, ever-growing **heard set** so songs you already know never get recommended.
3. **Candidates:** take your top artists and tracks as seeds and ask Last.fm for similar artists and tracks. This is where "people with similar taste" comes from.
4. **Rank and filter:** drop anything in the heard set, favor artists you've never played, and keep at most one song per artist.
5. **Deliver:** look up each pick on Spotify and write the 10 songs to a private playlist.
6. **Feedback (later):** liked / disliked / already-heard signals feed into the next week's picks.

## Why not just use Spotify for recommendations?

Spotify has locked its Web API down considerably:

| Change | Effect on this project |
|---|---|
| Nov 2024: audio features, recommendations, and related artists removed for new apps | Similarity data comes from Last.fm / ListenBrainz instead |
| Feb 2026: Development Mode apps capped at **5 users**, and the app owner needs Premium | v1 is for the owner plus up to 4 friends |
| Feb 2026: `popularity` field, artist top tracks, batch lookups, and browse removed; search capped at 10 results | Mainstream-vs-niche signal comes from Last.fm listener counts |
| May 2025: the higher user limit ("extended quota") is only granted to registered businesses with ~250k monthly users | Public sign-up needs a different design (see PLAN.md → Phase 5) |
| `recently-played` only returns the last 50 plays | Poll it often and keep the history ourselves |

What still works and is all we need: top tracks and artists, recently played, Liked Songs, reading your own playlists, search, and creating and filling playlists.

## Architecture

All infrastructure is in Terraform, and the layout mirrors the MFE → BFF → API → DB pattern:

| Layer | Tech | Status |
|---|---|---|
| DB | DynamoDB (single table) | defined, not deployed |
| API | Python 3.12 Lambdas (stdlib only, no packaging) | API Lambda deployed |
| BFF | Node.js Lambda | planned (Phase 4) |
| MFE | React | planned (Phase 4) |
| Scheduling | EventBridge (hourly ingest, weekly playlist) | planned (Phase 3) |
| Secrets | SSM Parameter Store | planned (Phase 0) |

## Repo layout

```
lambda/api/handler.py      API Lambda: returns top tracks, recent plays, genres
scripts/spotify_auth.py    One-time OAuth flow that gets a Spotify refresh token
terraform/                 Lambda, API Gateway, IAM, DynamoDB
PLAN.md                    Roadmap + decision log
```

## Setup

Prerequisites: Python 3.12, Terraform, AWS CLI with credentials, and a Spotify developer app (the owner needs Premium) with redirect URI `http://127.0.0.1:3000/callback`.

1. Create `.env` in the repo root:
   ```
   SPOTIFY_CLIENT_ID=...
   SPOTIFY_CLIENT_SECRET=...
   SPOTIFY_REDIRECT_URI=http://127.0.0.1:3000/callback
   ```
2. Get a refresh token (opens a browser; writes `spotify_tokens.json`):
   ```
   pip install requests python-dotenv
   python scripts/spotify_auth.py
   ```
3. Create `terraform/terraform.tfvars` with `spotify_client_id`, `spotify_client_secret`, and `spotify_refresh_token`.
4. Deploy:
   ```
   cd terraform && terraform init && terraform apply
   ```

`.env`, `spotify_tokens.json`, `*.tfvars`, Terraform state, and `notes/` are gitignored. Never commit them.

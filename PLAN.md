# Plan

The living roadmap for this project. Update the checkboxes and the **Current focus** line as work lands, and add to the decision log whenever a design choice is made.

**Current focus:** Phase 0: push the new refresh token to SSM, commit.
**Last updated:** 2026-10-11

---

## Goal

Every week, deliver a Spotify playlist of 10 songs the user hasn't heard, picked using what listeners with similar taste play.

- **Near term:** the owner plus up to 4 friends (Spotify's Development Mode limit).
- **Long term:** public sign-up, which requires the design in Phase 5.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-11 | **≤5 users for now**, with the multi-user design kept | Spotify Development Mode caps apps at 5 users; the higher limit (extended quota) requires a registered business with ~250k monthly users |
| 2026-10-11 | **Similarity data from Last.fm** (v1), ListenBrainz later | Spotify removed related artists and recommendations; our own ≤5 users are too few for collaborative filtering; Last.fm has crowd-sourced similar artists and tracks and needs only an API key |
| 2026-10-11 | **Spotify is only an input (your listening) and an output (the playlist)** | Keeps the recommendation engine independent of Spotify, so the public path (Phase 5) doesn't mean a rewrite |
| 2026-10-11 | **Scheduled Lambda instead of AWS Glue** for ingest | The data is small and needs frequent polling; Glue has a per-run minimum charge and slow startup |
| 2026-10-11 | **Keep MFE → BFF → API → DB**, built after the core loop works | Learning goal; v1 feedback can come from Spotify itself |
| 2026-10-11 | **Weekly, 10 songs.** Get one manual run working before adding any scheduling | Prove the loop end to end first |
| 2026-10-11 | **No Spotify data export upload** in v1 | Old history says little about current taste; the privacy cost (IP addresses, devices) isn't worth it; the heard set is built from other sources (below). If revisited, parse it in the browser and upload only track ID, timestamp, and play duration |
| 2026-10-11 | **Taste = recent listening with older plays counting less; heard set = only ever grows** | 2014 listening shouldn't steer 2026 picks, but it should still prevent repeats |
| 2026-10-12 | **Last.fm scrobble history is the main listening-history source**, with Spotify as backup (Liked Songs, playlists, recent plays) | Real play-by-play history since 2021 vs. Spotify's last 50 plays |
| 2026-10-12 | **Song versions:** radio edit / extended / remaster / album vs. single / explicit vs. clean / live / acoustic / stripped = **same song** (never recommend if any version is heard). Remixes by another artist and covers = **different song** | Re-recommending a different version of a song you know isn't discovery (Last.fm's homepage did this with "Blame Brett") |
| 2026-10-11 | **Don't rely on Spotify `popularity`** | Officially removed in Feb 2026; our app still gets it for now. Use Last.fm listener counts for mainstream vs. niche |
| 2026-10-11 | **Drop the ARTIST#/TRACK# LISTENER cross-reference records** | Collaborative filtering across ≤5 users is pointless; Last.fm/ListenBrainz provide that signal |

## Spotify API: what we can and can't use

- ✅ `/me/top/tracks`, `/me/top/artists` (short ≈ 4 weeks, medium ≈ 6 months, long ≈ 1 year)
- ✅ `/me/player/recently-played`, last 50 plays only, so poll often and keep the history ourselves
- ✅ `/me/tracks` (Liked Songs, read in batches)
- ✅ `/me/playlists` and `/playlists/{id}/items`, only for playlists the user owns or collaborates on
- ✅ `/search`, max 10 results
- ✅ `POST /me/playlists`, `POST /playlists/{id}/items` (the old `/users/{id}/playlists` and `/tracks` paths were removed)
- ❌ recommendations, related artists, audio features, artist top tracks, browse, batch `/tracks` and `/artists` lookups, other users' profiles and playlists
- ⚠️ `popularity`, `genres`: still returned to our app today but not guaranteed

---

## Phase 0: Housekeeping and API verification

- [x] Commit the pending `terraform/main.tf` change (formatting + DynamoDB table) and `terraform apply`. The table is now deployed
- [x] Lock down the public API Gateway route: now `AWS_IAM` auth (public URL returns 403); test with `aws lambda invoke --function-name playlist-recommendation-engine-api out.json`
- [x] Move Spotify secrets out of Lambda environment variables into SSM Parameter Store (SecureString) under `/playlist-recommendation-engine/spotify/*`; the Lambda reads them at runtime. Values still come from `terraform.tfvars`, so they are also in local Terraform state
- [x] Update `scripts/spotify_auth.py` scopes: add `user-library-read playlist-read-private playlist-read-collaborative playlist-modify-private`
- [x] Re-run `scripts/spotify_auth.py` (done 2026-10-12, all 6 scopes granted)
- [ ] Copy the new refresh token into `terraform.tfvars` (done) and `terraform apply` (plan reviewed: 1 change, refresh_token only)
- [x] Verify with `scripts/verify_spotify.py [--write]`. Results (2026-10-12, new scopes):
  - ✅ Liked Songs, read in batches (3,298 songs), list my playlists (50 incl. private), read owned playlist items, top tracks long_term, search (returns ISRC + popularity), single artist lookup
  - ✅ create playlist (`POST /me/playlists`) + add items (`POST /playlists/{id}/items`): test playlist "API test (safe to delete)" created
  - ⚠️ Spotify genres are patchy: only 30 of 50 top artists have any, so use Last.fm tags as the main genre signal
- [x] Get a Last.fm API key (`LAST_FM_API_KEY` in `.env`) and run `scripts/verify_lastfm.py`. All 4 methods work; similar artists and tags are good even for niche artists (e.g. Oskar med K → electronic / deep tech, similar artists all in that scene)
  - ⚠️ `track.getSimilar` returns error 6 "Track not found" for titles Last.fm doesn't know. Phase 1 must skip those seeds, and try `autocorrect=1`
  - Only the API key is needed; the shared secret is only for user login flows (Phase 5)
  - ⚠️ Last.fm returns some names HTML-escaped (`Boys &amp; Blondes`), so `html.unescape` every name before matching or searching
- [x] Check Last.fm user history (`LAST_FM_USERNAME` in `.env`): **64,457 scrobbles from 2021-07-12 to 2026-07-24**, roughly 3–11k per half-year (declining over time). `user.getInfo` playcount showed 0 while scrobbling was disconnected (now correct). 0 loved tracks
- [x] **Scrobbling stopped on 2026-07-24** (likely an inactive Last.fm login). Reconnected 2026-10-12. The gap can't be recovered from the Spotify API (last 50 plays only); Spotify's short-term top tracks partly cover it
- [x] Confirm new scrobbles appear: confirmed 2026-10-12 (reconnecting also backfilled the last 50 Spotify plays)
  - ⚠️ The now-playing track (no `date`) appears on every page of `user.getRecentTracks`, so ingest must skip it
- [x] Remove the tracked `terraform/output.json` (leftover test output)

## Phase 1: One manual end-to-end run ← the milestone

Goal: run one command, get a playlist of 10 good songs in your Spotify account. No scheduling yet.

**1a. Shared code:** `lambda/common/`
- [ ] `spotify.py`: token refresh, GET with paging and retry on 429 (respect `Retry-After`), POST
- [ ] `lastfm.py`: thin client
- [ ] `store.py`: DynamoDB reads and writes for the data model below

**1b. Ingest Lambda:** `lambda/ingest/` (invoked manually)
- [ ] Last.fm history → `PLAY#` records + mark heard. The declining yearly counts are real (less listening), not missing data, so recent months are thin (~500 plays/month) and recency weighting must not be too aggressive (e.g. a half-life in months, not weeks). Backfill all ~64k scrobbles once (200 per page ≈ 325 requests), then fetch only new ones with `from=<last seen>`
- [ ] Spotify recent plays → `PLAY#` records + mark heard (backup for gaps in scrobbling)
- [ ] Top tracks (short/medium/long) and top artists → `TOPTRACK#`/`TOPARTIST#` + mark heard
- [ ] Liked Songs (all) → mark heard
- [ ] Tracks in your own playlists → mark heard
- [ ] Rebuild `PROFILE` from real play counts (artist weights + Last.fm tags, with older plays counting less)

**1c. Recommend Lambda:** `lambda/recommend/` (invoked manually)
- [ ] Seeds: top ~20 artists by profile weight + top ~20 short-term tracks
- [ ] Candidates: Last.fm `artist.getSimilar` → `artist.getTopTracks` for new artists; `track.getSimilar` for top tracks
- [ ] Score = Σ (similarity × seed weight) − penalties; at most 1 track per artist; target mix of ~7 new artists / ~3 deeper cuts from known artists
- [ ] Filter: drop the heard set, matching on any of:
  - Spotify track ID
  - ISRC (the same recording across single/album/deluxe releases)
  - normalized `artist|title`: lowercase, `html.unescape`, strip punctuation and "feat. X", strip version labels (`- Radio Edit`, `(Extended Mix)`, `(Remastered 2011)`, `(Album Version)`, `(Deluxe)`, `(Live)`, `(Acoustic)`, `(Stripped)`, `- Single Version`, clean/explicit), but keep `<Artist> Remix` in the key
  - unit tests for the normalizer with real examples ("Black To Gold - Radio Edit" = "Black to Gold")
- [ ] Never put two versions of the same song in one playlist
- [ ] Look up each song on Spotify via search; skip if there's no confident match
- [ ] Create the private playlist `Weekly Picks — <date>` and add the 10 songs; save a `PLAYLIST#` record
- [ ] Terraform for both Lambdas + IAM (DynamoDB, SSM)

**Done when:** you listen to the playlist and it's better than the DJ. Then iterate on scoring before moving on.

## Phase 2: Feedback loop

- [ ] Implicit feedback from Spotify: songs from a picks playlist you Liked → liked; songs you removed from the playlist → disliked; songs you played often → positive
- [ ] Feed feedback into scoring (liked songs become seeds, disliked artists get a penalty)
- [ ] Explicit liked / disliked / already-heard buttons come with the UI in Phase 4

## Phase 3: Scheduling

- [ ] EventBridge: ingest **hourly** (so no plays are missed beyond the 50-play window), recommend **weekly**
- [ ] Alerting on failures (CloudWatch alarm → email)
- [ ] Optional: Terraform remote state (S3 + lock)

## Phase 4: BFF + MFE

- [ ] Node.js BFF Lambda behind API Gateway with real auth (Spotify login → session, or Cognito)
- [ ] React MFE: connect Spotify, view weekly picks, liked/disliked/already-heard buttons, settings (new-artist ratio, niche vs. mainstream)
- [ ] Onboard up to 4 friends (add their emails to the Spotify dashboard allowlist)

## Phase 5: Public path (exploratory)

The 5-user cap only applies to people who log in to Spotify through the app. To grow beyond it:
- [ ] Users connect **Last.fm or ListenBrainz** instead of logging in to Spotify (history read by username; verify ownership via Last.fm's login flow or a ListenBrainz token)
- [ ] Playlists are created by **one Spotify account we control** and shared by link. **Check Spotify's Developer Policy before relying on this**
- [ ] Optionally deliver to Apple Music too, by matching songs on ISRC
- [ ] Sign-up page must say that Last.fm/ListenBrainz listening data is public

## Phase 6: Smarter ranking

- [ ] ListenBrainz similar-users / collaborative filtering recommendations as a second candidate source
- [ ] LLM re-ranking or explanations via Bedrock ("why this song")
- [ ] Context signals (time of day, activity data from Apple Watch / Garmin)

---

## DynamoDB data model (single table, `pk` / `sk`)

| pk | sk | Contents |
|---|---|---|
| `USER#<id>` | `PROFILE` | artist weights, tag weights, updated_at |
| `USER#<id>` | `PLAY#<played_at>` | track_id, artist_id, names (raw play events) |
| `USER#<id>` | `HEARD#<track_id>` | first_seen, source (play/liked/playlist/top/feedback), norm_key |
| `USER#<id>` | `TOPTRACK#<range>#<rank>` | track snapshot for that time range |
| `USER#<id>` | `TOPARTIST#<range>#<rank>` | artist snapshot + genres |
| `USER#<id>` | `PLAYLIST#<date>` | playlist_id, track_ids, scores, seeds used |
| `USER#<id>` | `FEEDBACK#<track_id>` | liked / disliked / already_heard, at |
| `USER#<id>` | `TOKEN` | Spotify refresh token (encrypted) once there's more than one user |

Cache (optional): `LASTFM#<method>#<key>` / `RESP` with a TTL, so Last.fm isn't hit again for the same seeds every week.

## Open questions

- How should a run behave when fewer than 10 confident candidates survive filtering: ship fewer, or relax filters?
- Should "deeper cuts from known artists" exist at all, or should every pick be a new artist?
- Playlist naming: a new playlist each week, or one rolling "Weekly Picks" playlist that's overwritten?

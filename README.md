# antijudolinator

Filters online-gambling ("judol") donation-message spam out of sociabuzz
donations before they hit your stream overlay, with a per-user dashboard to
review and confirm flagged messages. Confirmed messages teach the filter new
obfuscation patterns (symbol/leetspeak/lookalike-alphabet substitutions),
shared across all users on the same deployment.

## How it works

- Sociabuzz sends a webhook to `/webhook/sociabuzz/<your-webhook-token>` for
  each donation.
- The message is normalized (folds Greek/Cyrillic lookalikes, leetspeak
  digits, inserted separators, repeated characters) and checked against a
  shared, growing list of known gambling-promo patterns.
- Anything not confidently matched is pushed live to your OBS overlay
  (`/overlay/<your-overlay-token>`) and logged. Each streamer picks the
  alert's look (ready-made styles or custom HTML/CSS), sound, duration and
  optional text-to-speech in `/dashboard/settings`. In OBS, tick "Control
  audio via OBS" on the Browser Source to hear the sound and voice.
- Confidently-matched messages are suppressed from the overlay and queued in
  your dashboard for review.
- When confirming a message as gambling, the streamer ticks which of its
  words are gambling promo; those are added to the shared pattern store — the
  filter gets better for everyone on future messages. Admins can review and
  delete patterns at `/admin/patterns`.

## Running locally with Docker

```
cp .env.example .env
# edit .env: set SESSION_SECRET_KEY, ADMIN_BOOTSTRAP_USERNAME/PASSWORD,
# and DOMAIN (use e.g. ":80" for local testing without a real domain/HTTPS)
docker compose up -d --build
docker exec <app-container-name> python -m app.bootstrap_admin
```

Then log in at `http://localhost/login` with the bootstrap admin credentials,
create a user account for each streamer under `/admin/users`, and have each
user copy their webhook URL (into sociabuzz's webhook settings) and overlay
URL (as an OBS Browser Source) from `/dashboard/settings`.

## Running tests

```
python -m venv .venv
.venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
pytest
```

## Deploying

Point a real domain's DNS at your VPS, set `DOMAIN=yourdomain.com` in `.env`
(Caddy will provision HTTPS automatically), and run `docker compose up -d
--build`. The SQLite database persists in the `db-data` Docker volume.

### Backups

Snapshot the database (keeps the newest 7 in `/data/backups` inside the
volume). Run it nightly from the host's crontab:

```
0 4 * * * cd /path/to/antijudolinator && docker compose exec -T app python -m app.backup
```

Copy `/data/backups` off the server occasionally too — a backup on the same
disk won't survive losing the VPS.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FastAPI + SQLite app that filters Indonesian online-gambling ("judol") spam out of sociabuzz donation messages before they reach a streamer's OBS overlay. Multi-tenant: each user has their own webhook token, overlay token, and review queue; the gambling pattern list is **shared across all users** on a deployment.

## Commands

```
pip install -r requirements.txt                       # deps (venv in .venv/)
pytest                                                 # all tests
pytest tests/test_match.py::test_name                  # single test
uvicorn app.main:app --reload                          # dev server (run from repo root; templates/static use relative paths)
python -m app.bootstrap_admin                          # create first admin from ADMIN_BOOTSTRAP_* env vars
docker compose up -d --build                           # prod: app + Caddy (auto-HTTPS via DOMAIN in .env)
```

No linter/formatter is configured.

## Architecture

Request flow for a donation (`app/routes/webhook.py`):
1. `POST /webhook/sociabuzz/{webhook_token}` → look up active user by token. If the user saved their sociabuzz token in settings, the request's `Sb-Webhook-Token` header must match it (401 otherwise). Real sociabuzz payloads also carry `currency`, `amount_settled`, `email_supporter`, `media_*`, `item`, etc.; the app ignores those. Sociabuzz's "test webhook" button always resends the same `id`, so only the first test is stored.
2. `classifier.classify.classify_message` → `normalize.words()` splits the text into folded words, then `match.find_match()` checks them against all DB patterns (sorted longest-first). Matching is **word-based** to avoid cross-word false positives — see the rules in `match.py`'s docstring (short patterns only match whole words/word edges; fuzzy and in-word substring only for 5+ chars).
3. Every message is stored as a `Message` with status `clean` or `gambling`. A sociabuzz `id` in the payload is stored as `external_id` and used to ignore webhook retries.
4. Only `clean` messages become an alert: `overlay_template.build_alert_payload` returns `{html, duration_ms, sound_url, volume, tts_text}` from the user's template (`{{supporter}}`/`{{amount}}`/`{{message}}` placeholders, values HTML-escaped, amount as `Rp50.000`) and alert settings, and it's pushed over WebSocket (`ws_manager.manager`, in-process, keyed by overlay token) to `/ws/overlay/{overlay_token}`. The settings page's "Send test alert" uses the same function.
5. `gambling` messages wait in the user's `/dashboard` for review. "Confirm gambling" lets the user tick candidate words (`learn.extract_candidate_patterns`: no stopwords, ≥4 chars); `learn_from_confirmation` adds only ticked words that really occur in the message to the shared `Pattern` table (or bumps `match_count`). Admins delete bad patterns at `/admin/patterns`. "Not gambling" is never replayed to the overlay (too late by then).

Classifier pieces (`app/classifier/`):
- `normalize.py` — NFKC, strip zero-width chars, fold Greek/Cyrillic lookalikes and `$`/`@`, split into words, strip 2+ digit prefixes/suffixes (`slot88` → `slot`), fold leetspeak digits, collapse repeated chars, rejoin spelled-out letters (`s l o t`). Patterns are stored in this folded-word form.
- `tests/test_match.py` holds parametrized lists of normal donations that must stay clean and promos that must be flagged — extend them when changing matching.
- `seed_patterns.py` — starter list inserted by `store.seed_if_empty` on app startup (lifespan in `main.py`).

Auth: Starlette signed-cookie sessions (`SESSION_SECRET_KEY`, required — the app refuses to start without it), `bcrypt` directly. `auth.get_current_user` treats disabled users as logged out. Route guards are FastAPI dependencies `require_login` (dashboard.py) and `require_admin` (admin.py, builds on `require_login`); unauthenticated redirects are done by raising `HTTPException(303, Location=/login)`. Failed logins are rate-limited per IP in process memory. Admins create users at `/admin/users`; there is no self-signup yet.

Overlay page (`overlay.html`) sends a nonce-based CSP so HTML in user templates can't run scripts; it queues alerts (each waits for its sound + TTS and its minimum duration) and reconnects its WebSocket. TTS uses the browser's Indonesian voice if present, otherwise Google Translate's unofficial TTS audio URL (OBS's browser usually has no voices). `app/static/overlay.css` is shared by the overlay and the settings-page preview iframe — style changes go there, not in either page. Built-in styles live in `overlay_template.PRESETS`; built-in sounds are `app/static/sounds/*.wav`; uploaded sounds are stored in `uploads/sounds/` next to the DB and served by `routes/overlay.py`. Overlay sockets and the rate limiter are in-process, so the app must run as a **single uvicorn worker** (Dockerfile also passes `--proxy-headers` so client IPs come from Caddy).

## Conventions / gotchas

- **No migration framework.** `db.init_db()` runs `create_all` and then `_ensure_column(...)` for columns added after initial release. When adding a column to an existing table, add an `_ensure_column` call (see `tests/test_db_migration.py`).
- DB path comes from `DB_PATH` env (default `./antijudolinator.db`; `/data/...` in Docker volume). `tests/conftest.py` sets `DB_PATH` to a temp file **before** importing the app, and the `client` fixture drops/recreates all tables per test.
- `python -m app.backup` snapshots the DB to `backups/` next to it (keeps 7).
- Server-rendered Jinja2 templates in `app/templates/`; form POSTs return 303 redirects.

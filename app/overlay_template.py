"""Renders the customizable OBS overlay alert from a user's template and alert settings."""

import html

from app.models import User

DEFAULT_TEMPLATE = (
    '<span class="supporter">{{supporter}}</span>'
    '<span class="amount">{{amount}}</span>\n'
    '<div class="message">{{message}}</div>'
)

MAX_TEMPLATE_LENGTH = 20_000

PREVIEW_SAMPLE = {"supporter": "Budi Santoso", "amount": 50000, "message": "Semangat terus min!"}

# Ready-made styles for streamers who don't write HTML. Each targets the
# #alert box from app/static/overlay.css.
PRESETS: dict[str, str] = {
    "Default": DEFAULT_TEMPLATE,
    "Card": """<style>
  #alert { background: #fff; color: #1b1f24; border-left: 6px solid #ff9f1c; }
  #alert .supporter { font-size: 1rem; color: #555; }
  #alert .amount { display: block; margin: 0.15rem 0 0; color: #e08600; font-size: 1.6rem; font-weight: 800; }
</style>
<span class="supporter">{{supporter}} baru saja donasi</span>
<span class="amount">{{amount}}</span>
<div class="message">{{message}}</div>""",
    "Neon": """<style>
  #alert { background: #0a0014; border: 2px solid #ff2bd6; text-align: center;
    box-shadow: 0 0 18px #ff2bd6, inset 0 0 12px rgba(255, 43, 214, 0.35); }
  #alert .supporter { color: #3ff; text-shadow: 0 0 8px #3ff; font-size: 1.3rem; }
  #alert .amount { display: block; margin: 0.2rem 0; color: #ff2bd6; text-shadow: 0 0 10px #ff2bd6;
    font-size: 1.5rem; font-weight: 800; }
</style>
<span class="supporter">{{supporter}}</span>
<span class="amount">{{amount}}</span>
<div class="message">{{message}}</div>""",
    "Minimal": """<style>
  #alert { background: none; box-shadow: none; padding: 0; text-align: center;
    text-shadow: 0 2px 6px rgba(0, 0, 0, 0.9), 0 0 2px #000; }
  #alert .supporter { font-size: 1.4rem; }
  #alert .amount { color: #ffd166; font-size: 1.4rem; }
  #alert .message { font-size: 1.1rem; }
</style>
<span class="supporter">{{supporter}}</span>
<span class="amount">{{amount}}</span>
<div class="message">{{message}}</div>""",
}

BUILTIN_SOUNDS = {"chime": "Chime", "coin": "Coin", "bell": "Bell"}
BUILTIN_SOUND_PREFIX = "/static/sounds/"

# Google Translate's TTS rejects longer text.
_MAX_TTS_LENGTH = 200


def format_rupiah(amount: int) -> str:
    return f"Rp{amount:,}".replace(",", ".") if amount else ""


def render_overlay_html(template: str, supporter: str, amount: int, message: str) -> str:
    return (
        template.replace("{{supporter}}", html.escape(supporter or "Anonymous"))
        .replace("{{amount}}", html.escape(format_rupiah(amount)))
        .replace("{{message}}", html.escape(message or ""))
    )


def build_alert_payload(user: User, supporter: str, amount: int, message: str) -> dict:
    tts_text = None
    if user.tts_enabled and amount >= user.tts_min_amount:
        spoken_amount = f" donasi {amount} rupiah" if amount else ""
        tts_text = f"{supporter or 'Anonymous'}{spoken_amount}. {message}"[:_MAX_TTS_LENGTH]

    return {
        "html": render_overlay_html(
            user.overlay_template or DEFAULT_TEMPLATE, supporter, amount, message
        ),
        "duration_ms": user.alert_duration_seconds * 1000,
        "sound_url": user.alert_sound_url,
        "volume": user.alert_volume / 100,
        "tts_text": tts_text,
    }

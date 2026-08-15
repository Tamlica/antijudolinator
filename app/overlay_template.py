"""Renders the customizable OBS overlay alert box from a per-user template."""

import html

DEFAULT_TEMPLATE = (
    '<span class="supporter">{{supporter}}</span>'
    '<span class="amount">{{amount}}</span>\n'
    '<div class="message">{{message}}</div>'
)


PREVIEW_SAMPLE = {"supporter": "Budi Santoso", "amount": 50000, "message": "Semangat terus min!"}


def render_overlay_html(template: str, supporter: str, amount: int, message: str) -> str:
    amount_text = f"Rp{amount}" if amount else ""
    return (
        template.replace("{{supporter}}", html.escape(supporter or "Anonymous"))
        .replace("{{amount}}", html.escape(amount_text))
        .replace("{{message}}", html.escape(message or ""))
    )

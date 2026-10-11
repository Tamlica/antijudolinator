from app.overlay_template import DEFAULT_TEMPLATE, render_overlay_html


def test_substitutes_placeholders():
    result = render_overlay_html(
        "<b>{{supporter}}</b> gave {{amount}}: {{message}}",
        supporter="Budi",
        amount=50000,
        message="Semangat terus!",
    )
    assert result == "<b>Budi</b> gave Rp50.000: Semangat terus!"


def test_escapes_donor_supplied_html_in_supporter_and_message():
    result = render_overlay_html(
        "{{supporter}} says {{message}}",
        supporter="<img src=x onerror=alert(1)>",
        amount=0,
        message="<script>alert(2)</script>",
    )
    assert "<img" not in result
    assert "<script>" not in result
    assert "&lt;img src=x onerror=alert(1)&gt;" in result
    assert "&lt;script&gt;alert(2)&lt;/script&gt;" in result


def test_supporter_defaults_to_anonymous_when_blank():
    result = render_overlay_html("{{supporter}}", supporter="", amount=0, message="")
    assert result == "Anonymous"


def test_amount_placeholder_empty_when_zero():
    result = render_overlay_html("[{{amount}}]", supporter="X", amount=0, message="")
    assert result == "[]"


def test_default_template_renders_with_expected_classes():
    result = render_overlay_html(DEFAULT_TEMPLATE, supporter="Budi", amount=1000, message="hi")
    assert 'class="supporter"' in result
    assert "Budi" in result
    assert "Rp1.000" in result
    assert "hi" in result


def test_formats_amount_as_rupiah_with_thousand_dots():
    from app.overlay_template import format_rupiah

    assert format_rupiah(1500000) == "Rp1.500.000"
    assert format_rupiah(500) == "Rp500"
    assert format_rupiah(0) == ""


def _user(**overrides):
    from app.models import User

    fields = dict(
        overlay_template=None, alert_duration_seconds=10, alert_sound_url="/static/sounds/coin.wav",
        alert_volume=50, tts_enabled=True, tts_min_amount=10000,
    )
    fields.update(overrides)
    return User(**fields)


def test_alert_payload_carries_settings_and_tts_text():
    from app.overlay_template import build_alert_payload

    payload = build_alert_payload(_user(), "Budi", 20000, "semangat")

    assert payload["duration_ms"] == 10000
    assert payload["sound_url"] == "/static/sounds/coin.wav"
    assert payload["volume"] == 0.5
    assert payload["tts_text"] == "Budi donasi 20000 rupiah. semangat"
    assert "Rp20.000" in payload["html"]


def test_alert_payload_skips_tts_below_minimum_or_when_disabled():
    from app.overlay_template import build_alert_payload

    assert build_alert_payload(_user(), "Budi", 5000, "hi")["tts_text"] is None
    assert build_alert_payload(_user(tts_enabled=False), "Budi", 50000, "hi")["tts_text"] is None


def test_alert_payload_tts_text_is_capped():
    from app.overlay_template import build_alert_payload

    payload = build_alert_payload(_user(tts_min_amount=0), "Budi", 0, "a" * 500)
    assert len(payload["tts_text"]) == 200

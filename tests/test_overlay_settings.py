from app.auth import hash_password
from app.overlay_template import DEFAULT_TEMPLATE
from app.models import User


def _make_user(session, username="streamer1", password="pw"):
    user = User(username=username, password_hash=hash_password(password), role="user")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _login(client, username="streamer1", password="pw"):
    client.post("/login", data={"username": username, "password": password})


def test_settings_page_shows_default_template_when_none_set(client, db_session):
    _make_user(db_session)
    _login(client)

    response = client.get("/dashboard/settings")

    assert response.status_code == 200
    # The textarea's HTML-escaping scheme is a Jinja implementation detail
    # (e.g. &#34; vs &quot;), so check content that survives either scheme.
    assert "{{supporter}}" in response.text
    assert "{{amount}}" in response.text
    assert "{{message}}" in response.text
    assert DEFAULT_TEMPLATE not in response.text  # confirms it IS escaped, not raw


def test_saving_custom_template_persists_and_shows_on_settings_page(client, db_session):
    user = _make_user(db_session)
    _login(client)

    custom = "Donatur: {{supporter}} kasih {{amount}}"
    save_response = client.post(
        "/dashboard/settings/overlay-template",
        data={"overlay_template": custom},
        follow_redirects=False,
    )
    assert save_response.status_code == 303

    db_session.refresh(user)
    assert user.overlay_template == custom

    response = client.get("/dashboard/settings")
    assert custom in response.text


def test_saving_blank_template_resets_to_default(client, db_session):
    user = _make_user(db_session)
    user.overlay_template = "custom leftover"
    db_session.commit()
    _login(client)

    client.post(
        "/dashboard/settings/overlay-template",
        data={"overlay_template": "   "},
        follow_redirects=False,
    )

    db_session.refresh(user)
    assert user.overlay_template is None


def test_preview_endpoint_renders_unsaved_draft_without_persisting(client, db_session):
    user = _make_user(db_session)
    _login(client)

    response = client.post(
        "/dashboard/settings/overlay-template/preview",
        data={"template": "Hi {{supporter}}, you gave {{amount}}: {{message}}"},
    )

    assert response.status_code == 200
    assert "Budi Santoso" in response.text
    assert "Rp50.000" in response.text

    db_session.refresh(user)
    assert user.overlay_template is None  # preview must not persist anything


def test_preview_endpoint_requires_login(client):
    response = client.post(
        "/dashboard/settings/overlay-template/preview",
        data={"template": "hi {{supporter}}"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def _alert_form(**overrides):
    form = {"alert_duration_seconds": "12", "alert_volume": "60", "sound_choice": "none"}
    form.update(overrides)
    return form


def test_saving_alert_settings_with_builtin_sound_and_tts(client, db_session):
    user = _make_user(db_session)
    _login(client)

    response = client.post(
        "/dashboard/settings/alert",
        data=_alert_form(sound_choice="builtin:chime", tts_enabled="true", tts_min_amount="5000"),
        follow_redirects=False,
    )

    assert response.headers["location"].endswith("notice=alert-saved")
    db_session.refresh(user)
    assert user.alert_duration_seconds == 12
    assert user.alert_volume == 60
    assert user.alert_sound_url == "/static/sounds/chime.wav"
    assert user.tts_enabled is True
    assert user.tts_min_amount == 5000
    assert client.get("/static/sounds/chime.wav").status_code == 200


def test_sound_link_must_be_https(client, db_session):
    user = _make_user(db_session)
    _login(client)

    response = client.post(
        "/dashboard/settings/alert",
        data=_alert_form(sound_choice="url", sound_url="javascript:alert(1)"),
        follow_redirects=False,
    )

    assert response.headers["location"].endswith("notice=sound-bad-url")
    db_session.refresh(user)
    assert user.alert_sound_url is None


def test_uploading_sound_stores_and_serves_it_and_replacing_deletes_old(client, db_session):
    from app.routes.overlay import SOUND_UPLOAD_DIR

    user = _make_user(db_session)
    _login(client)

    client.post(
        "/dashboard/settings/alert",
        data=_alert_form(sound_choice="upload"),
        files={"sound_file": ("ding.mp3", b"ID3fake-mp3-bytes", "audio/mpeg")},
    )
    db_session.refresh(user)
    first_url = user.alert_sound_url
    assert first_url.startswith("/uploads/sounds/")
    assert client.get(first_url).content == b"ID3fake-mp3-bytes"

    # Saving again with "upload" but no new file keeps the current sound.
    client.post("/dashboard/settings/alert", data=_alert_form(sound_choice="upload"))
    db_session.refresh(user)
    assert user.alert_sound_url == first_url

    client.post("/dashboard/settings/alert", data=_alert_form(sound_choice="builtin:bell"))
    assert not (SOUND_UPLOAD_DIR / first_url.rsplit("/", 1)[1]).exists()


def test_uploading_wrong_file_type_or_oversized_is_rejected(client, db_session):
    _make_user(db_session)
    _login(client)

    bad_type = client.post(
        "/dashboard/settings/alert",
        data=_alert_form(sound_choice="upload"),
        files={"sound_file": ("evil.html", b"<script>", "text/html")},
        follow_redirects=False,
    )
    too_big = client.post(
        "/dashboard/settings/alert",
        data=_alert_form(sound_choice="upload"),
        files={"sound_file": ("big.mp3", b"x" * (1024 * 1024 + 1), "audio/mpeg")},
        follow_redirects=False,
    )

    assert bad_type.headers["location"].endswith("notice=sound-bad-file")
    assert too_big.headers["location"].endswith("notice=sound-bad-file")


def test_uploaded_sound_route_rejects_path_tricks(client):
    assert client.get("/uploads/sounds/..%2F..%2Fapp.db").status_code == 404
    assert client.get("/uploads/sounds/not-a-real-file.mp3").status_code == 404


def test_test_alert_reaches_connected_overlay(client, db_session):
    user = _make_user(db_session)
    _login(client)

    no_overlay = client.post("/dashboard/settings/test-alert", follow_redirects=False)
    assert no_overlay.headers["location"].endswith("notice=test-no-overlay")

    with client.websocket_connect(f"/ws/overlay/{user.overlay_token}") as ws:
        response = client.post("/dashboard/settings/test-alert", follow_redirects=False)
        payload = ws.receive_json()

    assert response.headers["location"].endswith("notice=test-sent")
    assert "Budi Santoso" in payload["html"]
    assert payload["duration_ms"] == 8000


def test_overlong_template_is_rejected(client, db_session):
    user = _make_user(db_session)
    _login(client)

    response = client.post(
        "/dashboard/settings/overlay-template",
        data={"overlay_template": "x" * 20_001},
        follow_redirects=False,
    )

    assert response.headers["location"].endswith("notice=template-too-long")
    db_session.refresh(user)
    assert user.overlay_template is None


def test_settings_page_lists_presets_and_shows_notices(client, db_session):
    _make_user(db_session)
    _login(client)

    response = client.get("/dashboard/settings?notice=test-no-overlay")

    assert 'class="error"' in response.text
    for name in ("Card", "Neon", "Minimal"):
        assert f'<option value="{name}">' in response.text

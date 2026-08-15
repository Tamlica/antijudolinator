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
    assert "Rp50000" in response.text

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

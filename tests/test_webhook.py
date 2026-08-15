from app.auth import hash_password
from app.models import Message, User


def _make_user(session, username="streamer1"):
    user = User(username=username, password_hash=hash_password("pw"), role="user")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_webhook_flags_known_pattern_as_gambling(client, db_session):
    user = _make_user(db_session)

    response = client.post(
        f"/webhook/sociabuzz/{user.webhook_token}",
        json={"message": "promo sl0t gacor daftar sekarang", "amount": 10000, "supporter": "Budi"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "gambling"

    stored = db_session.get(Message, response.json()["message_id"])
    assert stored.status == "gambling"
    assert stored.reviewed is False


def test_webhook_marks_unmatched_message_clean(client, db_session):
    user = _make_user(db_session)

    response = client.post(
        f"/webhook/sociabuzz/{user.webhook_token}",
        json={"message": "terima kasih dukungannya kak", "amount": 5000, "supporter": "Sari"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "clean"


def test_webhook_pushes_rendered_html_using_default_template(client, db_session):
    user = _make_user(db_session)

    with client.websocket_connect(f"/ws/overlay/{user.overlay_token}") as ws:
        client.post(
            f"/webhook/sociabuzz/{user.webhook_token}",
            json={"message": "semangat terus kak", "amount": 2000, "supporter": "Dedi"},
        )
        payload = ws.receive_json()

    assert "Dedi" in payload["html"]
    assert "Rp2000" in payload["html"]
    assert "semangat terus kak" in payload["html"]


def test_webhook_pushes_rendered_html_using_users_custom_template(client, db_session):
    user = _make_user(db_session)
    user.overlay_template = "Donatur: {{supporter}} | {{amount}} | {{message}}"
    db_session.commit()

    with client.websocket_connect(f"/ws/overlay/{user.overlay_token}") as ws:
        client.post(
            f"/webhook/sociabuzz/{user.webhook_token}",
            json={"message": "makasih kak", "amount": 3000, "supporter": "Rian"},
        )
        payload = ws.receive_json()

    assert payload["html"] == "Donatur: Rian | Rp3000 | makasih kak"


def test_webhook_escapes_html_in_donor_supplied_fields(client, db_session):
    user = _make_user(db_session)

    with client.websocket_connect(f"/ws/overlay/{user.overlay_token}") as ws:
        client.post(
            f"/webhook/sociabuzz/{user.webhook_token}",
            json={
                "message": "<img src=x onerror=alert(1)>",
                "amount": 1000,
                "supporter": "Attacker",
            },
        )
        payload = ws.receive_json()

    assert "<img" not in payload["html"]
    assert "&lt;img" in payload["html"]


def test_webhook_rejects_unknown_token(client):
    response = client.post(
        "/webhook/sociabuzz/not-a-real-token",
        json={"message": "hello", "amount": 100, "supporter": "X"},
    )
    assert response.status_code == 404

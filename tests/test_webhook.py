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


def test_webhook_pushes_clean_message_to_overlay_websocket(client, db_session):
    user = _make_user(db_session)

    with client.websocket_connect(f"/ws/overlay/{user.overlay_token}") as ws:
        client.post(
            f"/webhook/sociabuzz/{user.webhook_token}",
            json={"message": "semangat terus kak", "amount": 2000, "supporter": "Dedi"},
        )
        payload = ws.receive_json()

    assert payload["supporter"] == "Dedi"
    assert payload["amount"] == 2000
    assert payload["message"] == "semangat terus kak"


def test_webhook_rejects_unknown_token(client):
    response = client.post(
        "/webhook/sociabuzz/not-a-real-token",
        json={"message": "hello", "amount": 100, "supporter": "X"},
    )
    assert response.status_code == 404

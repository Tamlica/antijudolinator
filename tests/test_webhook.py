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
    assert "Rp2.000" in payload["html"]
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

    assert payload["html"] == "Donatur: Rian | Rp3.000 | makasih kak"


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


def test_webhook_retry_with_same_id_is_not_stored_twice(client, db_session):
    user = _make_user(db_session)
    body = {"id": "sb-123", "message": "semangat kak", "amount": 1000, "supporter": "A"}

    first = client.post(f"/webhook/sociabuzz/{user.webhook_token}", json=body).json()
    second = client.post(f"/webhook/sociabuzz/{user.webhook_token}", json=body).json()

    assert second["message_id"] == first["message_id"]
    assert second["duplicate"] is True
    assert db_session.query(Message).filter_by(user_id=user.id).count() == 1


def test_overlay_page_sends_csp_that_blocks_template_scripts(client, db_session):
    user = _make_user(db_session)

    response = client.get(f"/overlay/{user.overlay_token}")

    csp = response.headers["content-security-policy"]
    assert "script-src 'nonce-" in csp
    nonce = csp.split("'nonce-")[1].split("'")[0]
    assert f'<script nonce="{nonce}">' in response.text


def test_overlay_socket_rejects_unknown_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/overlay/not-a-real-token") as ws:
            ws.receive_json()


def test_webhook_requires_matching_sociabuzz_token_once_set(client, db_session):
    user = _make_user(db_session)
    user.sociabuzz_webhook_token = "sbwhook-secret"
    db_session.commit()
    url = f"/webhook/sociabuzz/{user.webhook_token}"
    body = {"message": "halo", "amount": 1000, "supporter": "A"}

    assert client.post(url, json=body).status_code == 401
    assert client.post(url, json=body, headers={"Sb-Webhook-Token": "wrong"}).status_code == 401
    assert client.post(url, json=body, headers={"Sb-Webhook-Token": "sbwhook-secret"}).status_code == 200
    assert db_session.query(Message).filter_by(user_id=user.id).count() == 1


def test_webhook_accepts_requests_without_header_when_token_not_set(client, db_session):
    user = _make_user(db_session)
    response = client.post(
        f"/webhook/sociabuzz/{user.webhook_token}", json={"message": "halo", "supporter": "A"}
    )
    assert response.status_code == 200

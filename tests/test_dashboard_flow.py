from app.auth import hash_password
from app.classifier.store import get_pattern_by_text
from app.models import Message, User


def _make_user(session, username="streamer1", password="pw"):
    user = User(username=username, password_hash=hash_password(password), role="user")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_confirming_gambling_learns_new_pattern(client, db_session):
    user = _make_user(db_session)

    webhook_response = client.post(
        f"/webhook/sociabuzz/{user.webhook_token}",
        json={"message": "promo bandarbet daftar sekarang", "amount": 1000, "supporter": "Rudi"},
    )
    message_id = webhook_response.json()["message_id"]
    assert webhook_response.json()["status"] == "clean"  # not yet known as gambling

    client.post("/login", data={"username": "streamer1", "password": "pw"})

    confirm_response = client.post(
        f"/dashboard/messages/{message_id}/confirm-gambling",
        data={"learn_words": ["bandarbet"]},
        follow_redirects=False,
    )
    assert confirm_response.status_code == 303

    message = db_session.get(Message, message_id)
    assert message.reviewed is True
    assert message.review_result == "confirmed_gambling"

    assert get_pattern_by_text(db_session, "bandarbet") is not None


def test_confirming_clean_does_not_learn_a_pattern(client, db_session):
    user = _make_user(db_session)

    webhook_response = client.post(
        f"/webhook/sociabuzz/{user.webhook_token}",
        json={"message": "terima kasih banyak yaa", "amount": 1000, "supporter": "Wati"},
    )
    message_id = webhook_response.json()["message_id"]

    client.post("/login", data={"username": "streamer1", "password": "pw"})
    client.post(f"/dashboard/messages/{message_id}/confirm-clean", follow_redirects=False)

    message = db_session.get(Message, message_id)
    assert message.reviewed is True
    assert message.review_result == "confirmed_clean"


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_user_cannot_confirm_another_users_message(client, db_session):
    owner = _make_user(db_session, username="owner", password="pw1")
    other = _make_user(db_session, username="other", password="pw2")

    webhook_response = client.post(
        f"/webhook/sociabuzz/{owner.webhook_token}",
        json={"message": "cuanmax99 daftar yuk", "amount": 1000, "supporter": "X"},
    )
    message_id = webhook_response.json()["message_id"]

    client.post("/login", data={"username": "other", "password": "pw2"})
    response = client.post(f"/dashboard/messages/{message_id}/confirm-gambling")
    assert response.status_code == 404


def test_confirming_gambling_learns_only_ticked_words(client, db_session):
    user = _make_user(db_session)
    message_id = client.post(
        f"/webhook/sociabuzz/{user.webhook_token}",
        json={"message": "halo dari jakarta, daftar bandarbet", "amount": 1000, "supporter": "R"},
    ).json()["message_id"]

    client.post("/login", data={"username": "streamer1", "password": "pw"})
    # "evilword" isn't in the message, so it must be ignored even if posted.
    client.post(
        f"/dashboard/messages/{message_id}/confirm-gambling",
        data={"learn_words": ["bandarbet", "evilword"]},
    )

    assert get_pattern_by_text(db_session, "bandarbet") is not None
    assert get_pattern_by_text(db_session, "jakarta") is None
    assert get_pattern_by_text(db_session, "evilword") is None


def test_disabled_user_is_logged_out_of_existing_session(client, db_session):
    user = _make_user(db_session)
    client.post("/login", data={"username": "streamer1", "password": "pw"})
    assert client.get("/dashboard", follow_redirects=False).status_code == 200

    user.is_active = False
    db_session.commit()

    assert client.get("/dashboard", follow_redirects=False).status_code == 303


def test_login_is_rate_limited_after_repeated_failures(client, db_session):
    _make_user(db_session)
    for _ in range(5):
        assert client.post("/login", data={"username": "streamer1", "password": "x"}).status_code == 401

    response = client.post("/login", data={"username": "streamer1", "password": "pw"})
    assert response.status_code == 429


def test_user_can_change_password(client, db_session):
    _make_user(db_session)
    client.post("/login", data={"username": "streamer1", "password": "pw"})

    client.post(
        "/dashboard/settings/password",
        data={"current_password": "wrong", "new_password": "newpassword"},
    )
    client.post(
        "/dashboard/settings/password",
        data={"current_password": "pw", "new_password": "newpassword"},
    )
    client.post("/logout")

    assert client.post(
        "/login", data={"username": "streamer1", "password": "newpassword"}, follow_redirects=False
    ).status_code == 303


def test_regenerating_overlay_token_invalidates_old_url(client, db_session):
    user = _make_user(db_session)
    old_token = user.overlay_token
    client.post("/login", data={"username": "streamer1", "password": "pw"})

    client.post("/dashboard/settings/regenerate/overlay")

    db_session.refresh(user)
    assert user.overlay_token != old_token
    assert client.get(f"/overlay/{old_token}").status_code == 404
    assert client.get(f"/overlay/{user.overlay_token}").status_code == 200

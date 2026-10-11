from app.auth import hash_password
from app.models import User


def _make_admin(session, username="root", password="pw"):
    admin = User(username=username, password_hash=hash_password(password), role="admin")
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


def test_admin_can_create_user_with_generated_tokens(client, db_session):
    _make_admin(db_session)
    client.post("/login", data={"username": "root", "password": "pw"})

    response = client.post(
        "/admin/users", data={"username": "newstreamer", "password": "pw2"}, follow_redirects=False
    )
    assert response.status_code == 303

    created = db_session.query(User).filter_by(username="newstreamer").first()
    assert created is not None
    assert created.role == "user"
    assert created.webhook_token
    assert created.overlay_token
    assert created.webhook_token != created.overlay_token


def test_non_admin_cannot_access_admin_routes(client, db_session):
    user = User(username="plain", password_hash=hash_password("pw"), role="user")
    db_session.add(user)
    db_session.commit()

    client.post("/login", data={"username": "plain", "password": "pw"})
    response = client.get("/admin/users")
    assert response.status_code == 403


def test_admin_can_disable_a_user(client, db_session):
    admin = _make_admin(db_session)
    target = User(username="temp", password_hash=hash_password("pw"), role="user")
    db_session.add(target)
    db_session.commit()
    db_session.refresh(target)

    client.post("/login", data={"username": "root", "password": "pw"})
    client.post(f"/admin/users/{target.id}/toggle-active", follow_redirects=False)

    db_session.refresh(target)
    assert target.is_active is False


def test_creating_duplicate_username_shows_error(client, db_session):
    _make_admin(db_session)
    client.post("/login", data={"username": "root", "password": "pw"})

    response = client.post("/admin/users", data={"username": "root", "password": "pw2"})

    assert response.status_code == 400
    assert "already taken" in response.text


def test_admin_can_reset_a_users_password(client, db_session):
    _make_admin(db_session)
    target = User(username="temp", password_hash=hash_password("pw"), role="user")
    db_session.add(target)
    db_session.commit()

    client.post("/login", data={"username": "root", "password": "pw"})
    client.post(f"/admin/users/{target.id}/password", data={"new_password": "resetpass1"})
    client.post("/logout")

    assert client.post(
        "/login", data={"username": "temp", "password": "resetpass1"}, follow_redirects=False
    ).status_code == 303


def test_admin_can_delete_a_pattern(client, db_session):
    from app.classifier.store import get_pattern_by_text

    _make_admin(db_session)
    client.post("/login", data={"username": "root", "password": "pw"})
    pattern = get_pattern_by_text(db_session, "gacor")

    assert "gacor" in client.get("/admin/patterns").text
    client.post(f"/admin/patterns/{pattern.id}/delete")

    db_session.expire_all()
    assert get_pattern_by_text(db_session, "gacor") is None

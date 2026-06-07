"""Gaming Buddy backend API tests."""
import os
import time
import uuid
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

SEED_A = "novastrike@seed.gamingbuddy.app"
SEED_B = "pixelpanda@seed.gamingbuddy.app"
PWD = "seedpass123"


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def fresh_user(session):
    email = f"test_{uuid.uuid4().hex[:8]}@test.com"
    payload = {
        "email": email, "password": "Pass1234!", "username": f"tester_{uuid.uuid4().hex[:6]}",
        "age": 25, "country": "USA", "languages": ["English"], "bio": "hi",
        "profile_photo": "", "top_games": [{"name": "CS2", "hours": 100}]
    }
    r = session.post(f"{API}/auth/signup", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and "user" in data
    return {"email": email, "token": data["token"], "user": data["user"]}


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# Health
def test_root(session):
    r = session.get(f"{API}/", timeout=10)
    assert r.status_code == 200
    assert "Gaming Buddy" in r.json().get("message", "")


# Auth
def test_signup_returns_token(fresh_user):
    assert fresh_user["token"]
    assert fresh_user["user"]["email"] == fresh_user["email"].lower()


def test_login_seed_user(session):
    r = session.post(f"{API}/auth/login", json={"email": SEED_A, "password": PWD}, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data
    assert data["user"]["email"] == SEED_A


def test_login_invalid(session):
    r = session.post(f"{API}/auth/login", json={"email": SEED_A, "password": "wrong"}, timeout=10)
    assert r.status_code == 401


def test_get_me_requires_auth(session):
    r = session.get(f"{API}/auth/me", timeout=10)
    assert r.status_code == 401


def test_get_me_with_token(session, fresh_user):
    r = session.get(f"{API}/auth/me", headers=auth(fresh_user["token"]), timeout=10)
    assert r.status_code == 200
    assert r.json()["email"] == fresh_user["email"].lower()


# Feed
def test_swipe_feed(session, fresh_user):
    r = session.get(f"{API}/swipe/feed", headers=auth(fresh_user["token"]), timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "cards" in data and len(data["cards"]) > 0
    c = data["cards"][0]
    assert "match_percentage" in c
    assert "shared_games" in c
    assert 1 <= c["match_percentage"] <= 99
    assert data["daily_likes_limit"] == 20


# Standout
def test_standout(session, fresh_user):
    r = session.get(f"{API}/standout", headers=auth(fresh_user["token"]), timeout=15)
    assert r.status_code == 200
    profiles = r.json()["profiles"]
    assert len(profiles) <= 10
    assert len(profiles) > 0


# Swipe & match
def test_swipe_pass_then_like_decrements(session, fresh_user):
    feed = session.get(f"{API}/swipe/feed", headers=auth(fresh_user["token"])).json()
    cards = feed["cards"]
    assert len(cards) >= 2
    initial_used = feed["daily_likes_used"]

    # pass first
    r1 = session.post(f"{API}/swipe", headers=auth(fresh_user["token"]),
                      json={"target_user_id": cards[0]["id"], "action": "pass"})
    assert r1.status_code == 200
    assert r1.json()["matched"] is False

    # like second
    r2 = session.post(f"{API}/swipe", headers=auth(fresh_user["token"]),
                      json={"target_user_id": cards[1]["id"], "action": "like"})
    assert r2.status_code == 200

    me = session.get(f"{API}/auth/me", headers=auth(fresh_user["token"])).json()
    assert me["daily_likes_used"] == initial_used + 1


def test_superlike_decrements(session):
    # Fresh user to have full super likes
    email = f"sl_{uuid.uuid4().hex[:8]}@test.com"
    r = session.post(f"{API}/auth/signup", json={
        "email": email, "password": "Pass1!", "username": f"sl{uuid.uuid4().hex[:6]}",
        "age": 22, "country": "USA", "languages": ["English"], "bio": "",
        "top_games": [{"name": "CS2", "hours": 50}]
    })
    assert r.status_code == 200
    tok = r.json()["token"]
    assert r.json()["user"]["super_likes_remaining"] == 1
    feed = session.get(f"{API}/swipe/feed", headers=auth(tok)).json()
    target = feed["cards"][0]["id"]
    sl = session.post(f"{API}/swipe", headers=auth(tok),
                      json={"target_user_id": target, "action": "superlike"})
    assert sl.status_code == 200
    me = session.get(f"{API}/auth/me", headers=auth(tok)).json()
    assert me["super_likes_remaining"] == 0

    # 2nd superlike should fail
    feed2 = session.get(f"{API}/swipe/feed", headers=auth(tok)).json()
    if feed2["cards"]:
        t2 = feed2["cards"][0]["id"]
        sl2 = session.post(f"{API}/swipe", headers=auth(tok),
                           json={"target_user_id": t2, "action": "superlike"})
        assert sl2.status_code == 429


def test_mutual_like_creates_match(session):
    # Two fresh users
    def signup(suffix):
        email = f"mutu_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
        r = session.post(f"{API}/auth/signup", json={
            "email": email, "password": "Pass1!", "username": f"mu{suffix}{uuid.uuid4().hex[:5]}",
            "age": 25, "country": "USA", "languages": ["English"], "bio": "",
            "top_games": [{"name": "CS2", "hours": 100}]
        })
        assert r.status_code == 200, r.text
        return r.json()
    a = signup("a")
    b = signup("b")
    # A likes B
    r1 = session.post(f"{API}/swipe", headers=auth(a["token"]),
                      json={"target_user_id": b["user"]["id"], "action": "like"})
    assert r1.status_code == 200
    assert r1.json()["matched"] is False
    # B likes A -> match
    r2 = session.post(f"{API}/swipe", headers=auth(b["token"]),
                      json={"target_user_id": a["user"]["id"], "action": "like"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["matched"] is True
    assert body["match_id"]
    match_id = body["match_id"]

    # GET matches for both
    ma = session.get(f"{API}/matches", headers=auth(a["token"])).json()
    assert any(m["match_id"] == match_id for m in ma["matches"])
    mb = session.get(f"{API}/matches", headers=auth(b["token"])).json()
    assert any(m["match_id"] == match_id for m in mb["matches"])

    # Messages flow
    snd = session.post(f"{API}/messages/{match_id}", headers=auth(a["token"]),
                       json={"text": "hello from A"})
    assert snd.status_code == 200
    assert snd.json()["text"] == "hello from A"
    time.sleep(0.5)
    snd2 = session.post(f"{API}/messages/{match_id}", headers=auth(b["token"]),
                        json={"text": "hi from B"})
    assert snd2.status_code == 200
    msgs = session.get(f"{API}/messages/{match_id}", headers=auth(a["token"])).json()
    assert len(msgs["messages"]) == 2
    assert msgs["other_user"]["id"] == b["user"]["id"]


def test_messages_unauthorized_match(session, fresh_user):
    r = session.get(f"{API}/messages/{uuid.uuid4()}", headers=auth(fresh_user["token"]))
    assert r.status_code == 404


def test_cannot_swipe_self(session, fresh_user):
    r = session.post(f"{API}/swipe", headers=auth(fresh_user["token"]),
                     json={"target_user_id": fresh_user["user"]["id"], "action": "like"})
    assert r.status_code == 400

"""Steam OpenID + Riot Games integration tests."""
import os
import uuid
import pytest
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

SEED_A = "novastrike@seed.gamingbuddy.app"
PWD = "seedpass123"


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def auth_token(session):
    # Use a fresh test user so we don't disturb seed data
    email = f"intg_{uuid.uuid4().hex[:8]}@test.com"
    r = session.post(f"{API}/auth/signup", json={
        "email": email, "password": "Pass1!", "username": f"intg{uuid.uuid4().hex[:6]}",
        "age": 24, "country": "USA", "languages": ["English"], "bio": "",
        "top_games": [{"name": "League of Legends", "hours": 100}]
    }, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Steam OpenID URL ----------
class TestSteamAuthUrl:
    def test_requires_auth(self, session):
        r = session.get(f"{API}/steam/auth-url?redirect_uri=https://example.com/cb", timeout=10)
        assert r.status_code == 401

    def test_returns_valid_openid_url(self, session, auth_token):
        r = session.get(
            f"{API}/steam/auth-url",
            params={"redirect_uri": "https://example.com/cb"},
            headers=auth(auth_token), timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "auth_url" in data
        url = data["auth_url"]
        assert url.startswith("https://steamcommunity.com/openid/login?")
        parsed = urlparse(url)
        q = parse_qs(parsed.query)
        assert q.get("openid.mode") == ["checkid_setup"]
        assert q.get("openid.ns") == ["http://specs.openid.net/auth/2.0"]
        # return_to must contain our callback + nonce param
        return_to = q.get("openid.return_to", [""])[0]
        assert "/api/steam/callback" in return_to
        assert "nonce=" in return_to


# ---------- Riot link ----------
class TestRiotLink:
    def test_invalid_riot_id_no_hash(self, session, auth_token):
        r = session.post(
            f"{API}/riot/link",
            json={"riot_id": "NoHashHere", "platform": "KR"},
            headers=auth(auth_token), timeout=20,
        )
        assert r.status_code == 400
        assert "gameName#tagLine" in r.json().get("detail", "") or "format" in r.json().get("detail", "").lower()

    def test_unknown_account_returns_400(self, session, auth_token):
        r = session.post(
            f"{API}/riot/link",
            json={"riot_id": f"NoSuchPlayer_{uuid.uuid4().hex[:6]}#ZZZZ", "platform": "KR"},
            headers=auth(auth_token), timeout=30,
        )
        # Could be 400 (not found) or 502 if Riot down. We expect 400 per the spec.
        assert r.status_code in (400, 502), r.text
        if r.status_code == 502:
            pytest.skip(f"Riot API unavailable: {r.text}")
        # If key expired the message will say so -> skip
        detail = r.json().get("detail", "")
        if "expired" in detail.lower() or "invalid" in detail.lower() and "key" in detail.lower():
            pytest.skip(f"Riot dev key expired: {detail}")

    def test_link_real_account_faker(self, session, auth_token):
        r = session.post(
            f"{API}/riot/link",
            json={"riot_id": "Hide on bush#KR1", "platform": "KR"},
            headers=auth(auth_token), timeout=30,
        )
        if r.status_code in (502,):
            pytest.skip(f"Riot API unavailable: {r.text}")
        if r.status_code == 400:
            detail = r.json().get("detail", "")
            if "expired" in detail.lower() or "invalid" in detail.lower():
                pytest.skip(f"Riot dev key expired: {detail}")
            pytest.fail(f"Unexpected 400: {detail}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "riot_id" in body
        prof = body.get("lol_profile", body)
        assert prof.get("summoner_level", 0) > 0
        # Verify via /api/auth/me
        me = session.get(f"{API}/auth/me", headers=auth(auth_token), timeout=15).json()
        assert me.get("riot_id"), "riot_id missing from /auth/me"
        assert me.get("lol_profile"), "lol_profile missing from /auth/me"
        lp = me["lol_profile"]
        assert "summoner_level" in lp
        assert "top_champions" in lp
        # Should have champion names mapped (not "Champion <id>")
        if lp["top_champions"]:
            for c in lp["top_champions"]:
                assert "champion_name" in c
                assert not c["champion_name"].startswith("Champion ")

    def test_riot_unlink(self, session, auth_token):
        # First ensure something is linked (best-effort)
        r = session.post(f"{API}/riot/unlink", headers=auth(auth_token), timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        me = session.get(f"{API}/auth/me", headers=auth(auth_token), timeout=15).json()
        assert not me.get("riot_id")
        assert not me.get("lol_profile")


# ---------- Steam unlink (without OpenID linking) ----------
class TestSteamUnlink:
    def test_steam_unlink_idempotent(self, session, auth_token):
        r = session.post(f"{API}/steam/unlink", headers=auth(auth_token), timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ---------- /auth/me shape includes new fields ----------
class TestAuthMeShape:
    def test_me_includes_integration_fields(self, session, auth_token):
        r = session.get(f"{API}/auth/me", headers=auth(auth_token), timeout=10)
        assert r.status_code == 200
        body = r.json()
        # Fields should be present (possibly null) since response_model was removed
        for key in ("riot_id", "lol_profile", "steam_persona_name", "top_games"):
            assert key in body, f"{key} missing in /auth/me"

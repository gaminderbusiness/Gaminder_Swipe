#!/usr/bin/env python3
"""
Comprehensive backend API test suite for Gaming Buddy
Tests all endpoints with real-looking data
"""
import requests
import json
import time
from typing import Dict, Optional

# Backend URL from frontend/.env
BASE_URL = "https://active-gamers-2.preview.emergentagent.com/api"

# Test credentials from test_credentials.md
SEED_USER_EMAIL = "novastrike@seed.gamingbuddy.app"
SEED_USER_PASSWORD = "seedpass123"

SEED_USER_2_EMAIL = "pixelpanda@seed.gamingbuddy.app"
SEED_USER_2_PASSWORD = "seedpass123"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name: str, details: str = ""):
    """Log a passed test"""
    msg = f"✅ {test_name}"
    if details:
        msg += f" - {details}"
    print(msg)
    test_results["passed"].append(test_name)

def log_fail(test_name: str, details: str):
    """Log a failed test"""
    msg = f"❌ {test_name} - {details}"
    print(msg)
    test_results["failed"].append(f"{test_name}: {details}")

def log_warning(test_name: str, details: str):
    """Log a warning"""
    msg = f"⚠️  {test_name} - {details}"
    print(msg)
    test_results["warnings"].append(f"{test_name}: {details}")

def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

# ============================================================================
# Test 1: Healthcheck
# ============================================================================
def test_healthcheck():
    print_section("TEST 1: Healthcheck")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("message") == "Gaming Buddy API":
                log_pass("Healthcheck", f"Status: {response.status_code}, Message: {data.get('message')}")
                return True
            else:
                log_fail("Healthcheck", f"Unexpected message: {data}")
                return False
        else:
            log_fail("Healthcheck", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_fail("Healthcheck", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 2: Signup
# ============================================================================
def test_signup() -> Optional[Dict]:
    print_section("TEST 2: Signup")
    try:
        # Create a new user with realistic gaming data
        signup_data = {
            "email": f"testgamer{int(time.time())}@gamingbuddy.app",
            "password": "SecurePass123!",
            "username": f"ProGamer{int(time.time())}",
            "age": 25,
            "country": "USA",
            "languages": ["English"],
            "bio": "Competitive FPS player looking for ranked teammates. Diamond in Valorant, always positive vibes!",
            "top_games": [
                {"name": "Valorant", "hours": 850},
                {"name": "CS2", "hours": 620},
                {"name": "Apex Legends", "hours": 340}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                user = data["user"]
                # Verify user fields
                if (user.get("email") == signup_data["email"] and
                    user.get("username") == signup_data["username"] and
                    user.get("age") == signup_data["age"] and
                    "daily_likes_used" in user and
                    "super_likes_remaining" in user):
                    log_pass("Signup", f"User created: {user.get('username')}, Token received")
                    return data
                else:
                    log_fail("Signup", f"User data incomplete: {user}")
                    return None
            else:
                log_fail("Signup", f"Missing token or user in response: {data}")
                return None
        else:
            log_fail("Signup", f"Status code: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        log_fail("Signup", f"Exception: {str(e)}")
        return None

# ============================================================================
# Test 3: Login (with seed user)
# ============================================================================
def test_login() -> Optional[Dict]:
    print_section("TEST 3: Login (Seed User)")
    try:
        login_data = {
            "email": SEED_USER_EMAIL,
            "password": SEED_USER_PASSWORD
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                user = data["user"]
                log_pass("Login", f"Logged in as: {user.get('username')}, Token: {data['token'][:20]}...")
                return data
            else:
                log_fail("Login", f"Missing token or user: {data}")
                return None
        else:
            log_fail("Login", f"Status code: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        log_fail("Login", f"Exception: {str(e)}")
        return None

# ============================================================================
# Test 4: Login with wrong password (401 test)
# ============================================================================
def test_login_wrong_password():
    print_section("TEST 4: Login with Wrong Password (401 Test)")
    try:
        login_data = {
            "email": SEED_USER_EMAIL,
            "password": "wrongpassword123"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=10)
        
        if response.status_code == 401:
            log_pass("Login Wrong Password", "Correctly returned 401 for invalid credentials")
            return True
        else:
            log_fail("Login Wrong Password", f"Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        log_fail("Login Wrong Password", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 5: Get /auth/me
# ============================================================================
def test_get_me(token: str):
    print_section("TEST 5: GET /auth/me")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        
        if response.status_code == 200:
            user = response.json()
            # Check required fields
            required_fields = ["id", "email", "username", "age", "country", "languages", 
                             "daily_likes_used", "super_likes_remaining"]
            missing_fields = [f for f in required_fields if f not in user]
            
            if not missing_fields:
                log_pass("GET /auth/me", f"User: {user.get('username')}, Likes: {user.get('daily_likes_used')}/20, Super: {user.get('super_likes_remaining')}")
                return user
            else:
                log_fail("GET /auth/me", f"Missing fields: {missing_fields}")
                return None
        else:
            log_fail("GET /auth/me", f"Status code: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        log_fail("GET /auth/me", f"Exception: {str(e)}")
        return None

# ============================================================================
# Test 6: Update Profile
# ============================================================================
def test_update_profile(token: str):
    print_section("TEST 6: PUT /profile/me")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        update_data = {
            "bio": "Updated bio: Looking for chill gaming sessions and ranked grind partners!",
            "languages": ["English", "Spanish"]
        }
        
        response = requests.put(f"{BASE_URL}/profile/me", json=update_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user = response.json()
            if user.get("bio") == update_data["bio"] and user.get("languages") == update_data["languages"]:
                log_pass("PUT /profile/me", f"Profile updated successfully")
                return True
            else:
                log_fail("PUT /profile/me", f"Update not reflected: {user}")
                return False
        else:
            log_fail("PUT /profile/me", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("PUT /profile/me", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 7: Swipe Feed
# ============================================================================
def test_swipe_feed(token: str):
    print_section("TEST 7: GET /swipe/feed")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/swipe/feed", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            cards = data.get("cards", [])
            
            if len(cards) > 0:
                # Check first card structure
                card = cards[0]
                required_fields = ["id", "username", "match_percentage", "shared_games"]
                missing_fields = [f for f in required_fields if f not in card]
                
                if not missing_fields:
                    # Verify match_percentage is 1-99
                    match_pct = card.get("match_percentage")
                    if 1 <= match_pct <= 99:
                        log_pass("GET /swipe/feed", f"Got {len(cards)} cards, Match%: {match_pct}, Shared games: {len(card.get('shared_games', []))}")
                        return cards
                    else:
                        log_fail("GET /swipe/feed", f"match_percentage out of range (1-99): {match_pct}")
                        return None
                else:
                    log_fail("GET /swipe/feed", f"Card missing fields: {missing_fields}")
                    return None
            else:
                log_warning("GET /swipe/feed", "No cards returned (all users swiped?)")
                return []
        else:
            log_fail("GET /swipe/feed", f"Status code: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        log_fail("GET /swipe/feed", f"Exception: {str(e)}")
        return None

# ============================================================================
# Test 8: Swipe Actions (like, pass, superlike)
# ============================================================================
def test_swipe_actions(token: str, cards: list):
    print_section("TEST 8: POST /swipe (like, pass, superlike)")
    
    if not cards or len(cards) < 3:
        log_warning("POST /swipe", "Not enough cards to test swipe actions")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 8a: Pass
    try:
        swipe_data = {
            "target_user_id": cards[0]["id"],
            "action": "pass"
        }
        response = requests.post(f"{BASE_URL}/swipe", json=swipe_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "matched" in data:
                log_pass("POST /swipe (pass)", f"Pass recorded, matched: {data.get('matched')}")
            else:
                log_fail("POST /swipe (pass)", f"Missing 'matched' field: {data}")
                return False
        else:
            log_fail("POST /swipe (pass)", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("POST /swipe (pass)", f"Exception: {str(e)}")
        return False
    
    # Test 8b: Like
    try:
        swipe_data = {
            "target_user_id": cards[1]["id"],
            "action": "like"
        }
        response = requests.post(f"{BASE_URL}/swipe", json=swipe_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            log_pass("POST /swipe (like)", f"Like recorded, matched: {data.get('matched')}")
        else:
            log_fail("POST /swipe (like)", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("POST /swipe (like)", f"Exception: {str(e)}")
        return False
    
    # Test 8c: Superlike
    try:
        swipe_data = {
            "target_user_id": cards[2]["id"],
            "action": "superlike"
        }
        response = requests.post(f"{BASE_URL}/swipe", json=swipe_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            log_pass("POST /swipe (superlike)", f"Superlike recorded, matched: {data.get('matched')}")
        else:
            log_fail("POST /swipe (superlike)", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("POST /swipe (superlike)", f"Exception: {str(e)}")
        return False
    
    return True

# ============================================================================
# Test 9: Self-swipe (should return 400)
# ============================================================================
def test_self_swipe(token: str, user_id: str):
    print_section("TEST 9: POST /swipe (self-swipe - should fail)")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        swipe_data = {
            "target_user_id": user_id,
            "action": "like"
        }
        response = requests.post(f"{BASE_URL}/swipe", json=swipe_data, headers=headers, timeout=10)
        
        if response.status_code == 400:
            log_pass("POST /swipe (self-swipe)", "Correctly returned 400 for self-swipe")
            return True
        else:
            log_fail("POST /swipe (self-swipe)", f"Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        log_fail("POST /swipe (self-swipe)", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 10: Match Creation (mutual likes)
# ============================================================================
def test_match_creation():
    print_section("TEST 10: Match Creation (Mutual Likes)")
    try:
        # Login as user 1
        login1 = requests.post(f"{BASE_URL}/auth/login", json={
            "email": SEED_USER_EMAIL,
            "password": SEED_USER_PASSWORD
        }, timeout=10).json()
        token1 = login1["token"]
        user1_id = login1["user"]["id"]
        
        # Login as user 2
        login2 = requests.post(f"{BASE_URL}/auth/login", json={
            "email": SEED_USER_2_EMAIL,
            "password": SEED_USER_2_PASSWORD
        }, timeout=10).json()
        token2 = login2["token"]
        user2_id = login2["user"]["id"]
        
        # User 1 likes User 2
        headers1 = {"Authorization": f"Bearer {token1}"}
        swipe1 = requests.post(f"{BASE_URL}/swipe", json={
            "target_user_id": user2_id,
            "action": "like"
        }, headers=headers1, timeout=10).json()
        
        # User 2 likes User 1 (should create match)
        headers2 = {"Authorization": f"Bearer {token2}"}
        swipe2 = requests.post(f"{BASE_URL}/swipe", json={
            "target_user_id": user1_id,
            "action": "like"
        }, headers=headers2, timeout=10).json()
        
        if swipe2.get("matched") == True and swipe2.get("match_id"):
            log_pass("Match Creation", f"Match created: {swipe2.get('match_id')}")
            return swipe2.get("match_id")
        else:
            log_fail("Match Creation", f"Match not created: {swipe2}")
            return None
    except Exception as e:
        log_fail("Match Creation", f"Exception: {str(e)}")
        return None

# ============================================================================
# Test 11: Standout (Top 10 Compatibility)
# ============================================================================
def test_standout(token: str):
    print_section("TEST 11: GET /standout")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/standout", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            profiles = data.get("profiles", [])
            
            if len(profiles) > 0 and len(profiles) <= 10:
                # Check if sorted by match_percentage
                percentages = [p.get("match_percentage", 0) for p in profiles]
                is_sorted = all(percentages[i] >= percentages[i+1] for i in range(len(percentages)-1))
                
                if is_sorted:
                    log_pass("GET /standout", f"Got {len(profiles)} profiles, sorted by match%: {percentages[:3]}")
                    return True
                else:
                    log_fail("GET /standout", f"Profiles not sorted by match%: {percentages}")
                    return False
            elif len(profiles) == 0:
                log_warning("GET /standout", "No profiles returned (all users swiped?)")
                return True
            else:
                log_fail("GET /standout", f"Too many profiles: {len(profiles)} (expected max 10)")
                return False
        else:
            log_fail("GET /standout", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("GET /standout", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 12: Matches List
# ============================================================================
def test_matches_list(token: str):
    print_section("TEST 12: GET /matches")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/matches", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            
            log_pass("GET /matches", f"Got {len(matches)} matches")
            return matches
        else:
            log_fail("GET /matches", f"Status code: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        log_fail("GET /matches", f"Exception: {str(e)}")
        return None

# ============================================================================
# Test 13: Messages (GET/POST)
# ============================================================================
def test_messages(token: str, match_id: str):
    print_section("TEST 13: GET/POST /messages/{match_id}")
    
    if not match_id:
        log_warning("Messages", "No match_id provided, skipping message tests")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 13a: GET messages
    try:
        response = requests.get(f"{BASE_URL}/messages/{match_id}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            log_pass("GET /messages", f"Got {len(messages)} messages for match {match_id}")
        else:
            log_fail("GET /messages", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("GET /messages", f"Exception: {str(e)}")
        return False
    
    # Test 13b: POST message
    try:
        message_data = {
            "text": "Hey! Want to team up for some ranked games? I'm usually online evenings EST."
        }
        response = requests.post(f"{BASE_URL}/messages/{match_id}", json=message_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            msg = response.json()
            if msg.get("text") == message_data["text"] and msg.get("id"):
                log_pass("POST /messages", f"Message sent: {msg.get('id')}")
                return True
            else:
                log_fail("POST /messages", f"Message data incomplete: {msg}")
                return False
        else:
            log_fail("POST /messages", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("POST /messages", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 14: Messages with non-participant (should return 404)
# ============================================================================
def test_messages_non_participant(token: str, match_id: str):
    print_section("TEST 14: GET /messages (non-participant - should fail)")
    
    if not match_id:
        log_warning("Messages Non-Participant", "No match_id provided, skipping")
        return False
    
    try:
        # Login as a different user (ghostbyte)
        login = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "ghostbyte@seed.gamingbuddy.app",
            "password": "seedpass123"
        }, timeout=10).json()
        token_other = login["token"]
        
        headers = {"Authorization": f"Bearer {token_other}"}
        response = requests.get(f"{BASE_URL}/messages/{match_id}", headers=headers, timeout=10)
        
        if response.status_code == 404:
            log_pass("GET /messages (non-participant)", "Correctly returned 404 for non-participant")
            return True
        else:
            log_fail("GET /messages (non-participant)", f"Expected 404, got {response.status_code}")
            return False
    except Exception as e:
        log_fail("GET /messages (non-participant)", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 15: Steam Auth URL
# ============================================================================
def test_steam_auth_url(token: str):
    print_section("TEST 15: GET /steam/auth-url")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"redirect_uri": "https://example.com/callback"}
        response = requests.get(f"{BASE_URL}/steam/auth-url", params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            auth_url = data.get("auth_url", "")
            
            # Check if URL contains required OpenID parameters
            # Note: nonce may be URL-encoded as %3Fnonce%3D
            if ("steamcommunity.com/openid/login" in auth_url and
                "openid.mode=checkid_setup" in auth_url and
                ("nonce=" in auth_url or "%3Fnonce%3D" in auth_url)):
                log_pass("GET /steam/auth-url", "Steam OpenID URL generated correctly")
                return True
            else:
                log_fail("GET /steam/auth-url", f"Invalid Steam URL: {auth_url}")
                return False
        else:
            log_fail("GET /steam/auth-url", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("GET /steam/auth-url", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 16: Steam Unlink
# ============================================================================
def test_steam_unlink(token: str):
    print_section("TEST 16: POST /steam/unlink")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/steam/unlink", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") == True:
                log_pass("POST /steam/unlink", "Steam unlinked successfully")
                return True
            else:
                log_fail("POST /steam/unlink", f"Unexpected response: {data}")
                return False
        else:
            log_fail("POST /steam/unlink", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("POST /steam/unlink", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 17: Riot Link (with empty API key - should fail gracefully)
# ============================================================================
def test_riot_link(token: str):
    print_section("TEST 17: POST /riot/link (empty API key - should fail gracefully)")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        riot_data = {
            "riot_id": "TestPlayer#NA1",
            "platform": "NA1"
        }
        response = requests.post(f"{BASE_URL}/riot/link", json=riot_data, headers=headers, timeout=10)
        
        # Should return 400 or 502 with graceful error, not crash
        if response.status_code in [400, 502]:
            data = response.json()
            if "detail" in data:
                log_pass("POST /riot/link", f"Graceful error with empty API key: {response.status_code} - {data.get('detail')}")
                return True
            else:
                log_fail("POST /riot/link", f"Error response missing 'detail': {data}")
                return False
        else:
            log_fail("POST /riot/link", f"Unexpected status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("POST /riot/link", f"Exception (should not crash): {str(e)}")
        return False

# ============================================================================
# Test 18: Riot Unlink
# ============================================================================
def test_riot_unlink(token: str):
    print_section("TEST 18: POST /riot/unlink")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/riot/unlink", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") == True:
                log_pass("POST /riot/unlink", "Riot unlinked successfully")
                return True
            else:
                log_fail("POST /riot/unlink", f"Unexpected response: {data}")
                return False
        else:
            log_fail("POST /riot/unlink", f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        log_fail("POST /riot/unlink", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 19: Seed Users Check
# ============================================================================
def test_seed_users():
    print_section("TEST 19: Seed Users Check")
    try:
        # Try to login with multiple seed users
        seed_users = [
            "novastrike@seed.gamingbuddy.app",
            "pixelpanda@seed.gamingbuddy.app",
            "ghostbyte@seed.gamingbuddy.app",
            "lunaquest@seed.gamingbuddy.app"
        ]
        
        successful_logins = 0
        for email in seed_users:
            try:
                response = requests.post(f"{BASE_URL}/auth/login", json={
                    "email": email,
                    "password": "seedpass123"
                }, timeout=10)
                if response.status_code == 200:
                    successful_logins += 1
            except:
                pass
        
        if successful_logins >= 4:
            log_pass("Seed Users", f"{successful_logins} seed users verified (expected 20 total)")
            return True
        else:
            log_fail("Seed Users", f"Only {successful_logins} seed users found")
            return False
    except Exception as e:
        log_fail("Seed Users", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 20: Quota Enforcement
# ============================================================================
def test_quota_enforcement():
    print_section("TEST 20: Quota Enforcement (Daily Likes)")
    try:
        # Create a new user
        signup_data = {
            "email": f"quotatest{int(time.time())}@gamingbuddy.app",
            "password": "TestPass123!",
            "username": f"QuotaTest{int(time.time())}",
            "age": 24,
            "country": "USA",
            "languages": ["English"],
            "bio": "Testing quota limits",
            "top_games": [{"name": "Valorant", "hours": 100}]
        }
        
        signup_resp = requests.post(f"{BASE_URL}/auth/signup", json=signup_data, timeout=10)
        if signup_resp.status_code != 200:
            log_fail("Quota Enforcement", "Failed to create test user")
            return False
        
        token = signup_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get feed
        feed_resp = requests.get(f"{BASE_URL}/swipe/feed", headers=headers, timeout=10)
        if feed_resp.status_code != 200:
            log_fail("Quota Enforcement", "Failed to get feed")
            return False
        
        cards = feed_resp.json().get("cards", [])
        if len(cards) < 20:
            log_warning("Quota Enforcement", f"Not enough cards to test quota (only {len(cards)})")
            return True
        
        # Like 20 users (daily limit)
        for i in range(20):
            swipe_resp = requests.post(f"{BASE_URL}/swipe", json={
                "target_user_id": cards[i]["id"],
                "action": "like"
            }, headers=headers, timeout=10)
            
            if swipe_resp.status_code != 200:
                log_fail("Quota Enforcement", f"Failed to like user {i+1}")
                return False
        
        # Try to like 21st user (should fail with 429)
        if len(cards) > 20:
            swipe_resp = requests.post(f"{BASE_URL}/swipe", json={
                "target_user_id": cards[20]["id"],
                "action": "like"
            }, headers=headers, timeout=10)
            
            if swipe_resp.status_code == 429:
                log_pass("Quota Enforcement", "Daily like limit enforced (429 after 20 likes)")
                return True
            else:
                log_fail("Quota Enforcement", f"Expected 429, got {swipe_resp.status_code}")
                return False
        else:
            log_warning("Quota Enforcement", "Not enough cards to test 21st like")
            return True
            
    except Exception as e:
        log_fail("Quota Enforcement", f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 21: Activity Status Calculation
# ============================================================================
def test_activity_status(token: str):
    print_section("TEST 21: Activity Status Calculation")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get feed to check activity statuses
        response = requests.get(f"{BASE_URL}/swipe/feed", headers=headers, timeout=10)
        
        if response.status_code == 200:
            cards = response.json().get("cards", [])
            
            if len(cards) > 0:
                # Check if activity_status field exists and has valid values
                valid_statuses = ["online", "away", "offline"]
                statuses = [c.get("activity_status") for c in cards]
                
                if all(s in valid_statuses for s in statuses):
                    status_counts = {s: statuses.count(s) for s in valid_statuses}
                    log_pass("Activity Status", f"Valid statuses: {status_counts}")
                    return True
                else:
                    log_fail("Activity Status", f"Invalid statuses found: {statuses}")
                    return False
            else:
                log_warning("Activity Status", "No cards to check activity status")
                return True
        else:
            log_fail("Activity Status", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_fail("Activity Status", f"Exception: {str(e)}")
        return False

# ============================================================================
# Main Test Runner
# ============================================================================
def main():
    print("\n" + "="*80)
    print("  GAMING BUDDY BACKEND API TEST SUITE")
    print("="*80)
    print(f"  Base URL: {BASE_URL}")
    print("="*80 + "\n")
    
    # Test 1: Healthcheck
    test_healthcheck()
    
    # Test 2: Signup
    signup_result = test_signup()
    
    # Test 3: Login
    login_result = test_login()
    if not login_result:
        print("\n❌ CRITICAL: Login failed, cannot continue with authenticated tests")
        return
    
    token = login_result["token"]
    user_id = login_result["user"]["id"]
    
    # Test 4: Login with wrong password
    test_login_wrong_password()
    
    # Test 5: Get /auth/me
    test_get_me(token)
    
    # Test 6: Update profile
    test_update_profile(token)
    
    # Test 7: Swipe feed
    cards = test_swipe_feed(token)
    
    # Test 8: Swipe actions (use fresh signup user to ensure quotas available)
    if signup_result:
        signup_cards = test_swipe_feed(signup_result["token"])
        if signup_cards:
            test_swipe_actions(signup_result["token"], signup_cards)
    elif cards:
        test_swipe_actions(token, cards)
    
    # Test 9: Self-swipe
    test_self_swipe(token, user_id)
    
    # Test 10: Match creation
    match_id = test_match_creation()
    
    # Test 11: Standout
    test_standout(token)
    
    # Test 12: Matches list
    matches = test_matches_list(token)
    
    # Test 13: Messages
    if match_id:
        test_messages(token, match_id)
        # Test 14: Messages non-participant
        test_messages_non_participant(token, match_id)
    
    # Test 15: Steam auth URL
    test_steam_auth_url(token)
    
    # Test 16: Steam unlink
    test_steam_unlink(token)
    
    # Test 17: Riot link (empty API key)
    test_riot_link(token)
    
    # Test 18: Riot unlink
    test_riot_unlink(token)
    
    # Test 19: Seed users
    test_seed_users()
    
    # Test 20: Quota enforcement
    test_quota_enforcement()
    
    # Test 21: Activity status
    test_activity_status(token)
    
    # Print summary
    print_section("TEST SUMMARY")
    print(f"✅ Passed: {len(test_results['passed'])}")
    print(f"❌ Failed: {len(test_results['failed'])}")
    print(f"⚠️  Warnings: {len(test_results['warnings'])}")
    
    if test_results['failed']:
        print("\n❌ FAILED TESTS:")
        for fail in test_results['failed']:
            print(f"  - {fail}")
    
    if test_results['warnings']:
        print("\n⚠️  WARNINGS:")
        for warn in test_results['warnings']:
            print(f"  - {warn}")
    
    print("\n" + "="*80)
    if len(test_results['failed']) == 0:
        print("  ✅ ALL CRITICAL TESTS PASSED!")
    else:
        print(f"  ❌ {len(test_results['failed'])} TESTS FAILED")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()

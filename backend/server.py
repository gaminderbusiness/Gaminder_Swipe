from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import secrets
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from urllib.parse import quote, urlencode
import uuid
import bcrypt
from datetime import datetime, timezone, timedelta

from integrations import (
    build_steam_openid_url,
    verify_steam_openid,
    fetch_steam_profile_and_games,
    fetch_riot_lol_profile,
    load_champion_mapping,
)


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


# ---------- Constants ----------
PLAYTIME_SLOTS = [
    "00:00-03:00", "03:00-06:00", "06:00-09:00", "09:00-12:00",
    "12:00-15:00", "15:00-18:00", "18:00-21:00", "21:00-00:00",
]
INACTIVE_THRESHOLD = timedelta(days=7)
STEAM_CURRENT_GAME_TTL = timedelta(seconds=60)
MIN_COMPAT_TO_SHOW = 50
RIOT_RANK_TIERS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]


# ---------- Models ----------
class Game(BaseModel):
    name: str
    hours: int


class UserPublic(BaseModel):
    id: str
    username: str
    age: int
    country: str
    city: Optional[str] = None
    languages: List[str]
    bio: str
    profile_photo: str
    steam_avatar: Optional[str] = None
    steam_profile_url: Optional[str] = None
    top_games: List[Game] = []
    recently_played_games: List[str] = []
    playtime_slots: List[str] = []
    current_game: Optional[str] = None
    most_recent_game: Optional[str] = None
    most_recent_game_at: Optional[str] = None
    steam_total_hours: int = 0
    last_active: Optional[str] = None
    activity_status: Literal["online", "away", "offline"] = "offline"
    is_inactive: bool = False


class UserMe(UserPublic):
    email: str
    daily_likes_used: int = 0
    super_likes_remaining: int = 1
    like_reset_at: Optional[str] = None
    super_like_reset_at: Optional[str] = None
    standout_boost_until: Optional[str] = None
    is_admin: bool = False


class SignupBody(BaseModel):
    email: EmailStr
    password: str
    username: str
    age: int
    country: str
    city: Optional[str] = ""
    languages: List[str]
    bio: str = ""
    profile_photo: str = ""
    top_games: List[Game] = []
    recently_played_games: List[str] = []
    playtime_slots: List[str] = []


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileBody(BaseModel):
    username: Optional[str] = None
    age: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    languages: Optional[List[str]] = None
    bio: Optional[str] = None
    profile_photo: Optional[str] = None
    top_games: Optional[List[Game]] = None
    recently_played_games: Optional[List[str]] = None
    playtime_slots: Optional[List[str]] = None


class SwipeBody(BaseModel):
    target_user_id: str
    action: Literal["like", "pass", "superlike"]


class MessageBody(BaseModel):
    text: str


class AuthResp(BaseModel):
    token: str
    user: UserMe


# ---------- Auth helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def check_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    sess = await db.sessions.find_one({"token": token}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": sess["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # Update last_active
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_active": now().isoformat()}})
    return user


# ---------- Activity status helper ----------
def compute_activity(last_active_iso: Optional[str]) -> str:
    if not last_active_iso:
        return "offline"
    try:
        dt = datetime.fromisoformat(last_active_iso)
        delta = now() - dt
        if delta < timedelta(minutes=5):
            return "online"
        if delta < timedelta(hours=3):
            return "away"
        return "offline"
    except Exception:
        return "offline"


def public_user(u: dict) -> dict:
    last = u.get("last_active")
    is_inactive = bool(u.get("inactive_at")) and not _is_active_recently(last)
    return {
        "id": u["id"],
        "username": u["username"],
        "age": u["age"],
        "country": u["country"],
        "city": u.get("city"),
        "languages": u.get("languages", []),
        "bio": u.get("bio", ""),
        "profile_photo": u.get("profile_photo", ""),
        "steam_avatar": u.get("steam_avatar"),
        "steam_profile_url": u.get("steam_profile_url"),
        "steam_persona_name": u.get("steam_persona_name"),
        "steam_linked": bool(u.get("steam_id")),
        "top_games": u.get("top_games", []),
        "recently_played_games": u.get("recently_played_games", []),
        "playtime_slots": u.get("playtime_slots", []),
        "current_game": (u.get("current_steam_game") or {}).get("name") if u.get("current_steam_game") else None,
        "most_recent_game": u.get("most_recent_game"),
        "most_recent_game_at": u.get("most_recent_game_at"),
        "steam_total_hours": int(u.get("steam_total_hours", 0)),
        "riot_id": u.get("riot_id"),
        "riot_platform": u.get("riot_platform"),
        "lol_profile": u.get("lol_profile"),
        "last_active": last,
        "activity_status": compute_activity(last),
        "is_inactive": is_inactive,
    }


def _is_active_recently(last_iso: Optional[str]) -> bool:
    if not last_iso:
        return False
    try:
        return (now() - datetime.fromisoformat(last_iso)) < INACTIVE_THRESHOLD
    except Exception:
        return False


def me_user(u: dict) -> dict:
    base = public_user(u)
    base.update({
        "email": u["email"],
        "daily_likes_used": u.get("daily_likes_used", 0),
        "super_likes_remaining": u.get("super_likes_remaining", 1),
        "like_reset_at": u.get("like_reset_at"),
        "super_like_reset_at": u.get("super_like_reset_at"),
        "standout_boost_until": u.get("standout_boost_until"),
        "is_admin": bool(u.get("is_admin", False)),
        "onboarding_complete": bool(u.get("onboarding_complete", False)),
    })
    return base


# ---------- Like quota helpers ----------
async def refresh_quotas(user: dict) -> dict:
    n = now()
    updates = {}
    like_reset = user.get("like_reset_at")
    if not like_reset:
        updates["like_reset_at"] = (n + timedelta(hours=24)).isoformat()
        updates["daily_likes_used"] = 0
    else:
        try:
            if n > datetime.fromisoformat(like_reset):
                updates["like_reset_at"] = (n + timedelta(hours=24)).isoformat()
                updates["daily_likes_used"] = 0
        except Exception:
            pass

    sl_reset = user.get("super_like_reset_at")
    if not sl_reset:
        updates["super_like_reset_at"] = (n + timedelta(days=7)).isoformat()
        updates["super_likes_remaining"] = 1
    else:
        try:
            if n > datetime.fromisoformat(sl_reset):
                updates["super_like_reset_at"] = (n + timedelta(days=7)).isoformat()
                updates["super_likes_remaining"] = 1
        except Exception:
            pass

    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        user.update(updates)
    return user


# ---------- Compatibility scoring (v2 - spec compliant) ----------
def _ci_set(items: List[str]) -> set:
    return {s.strip().lower() for s in items if s}


def _rank_tier(rank: Optional[dict]) -> Optional[str]:
    if not rank:
        return None
    return (rank.get("tier") or "").upper() or None


def _tier_similar(t1: Optional[str], t2: Optional[str]) -> bool:
    """Per user spec: 'Gold Plat vs yeterli' - same tier OR ±1 tier counts."""
    if not t1 or not t2:
        return False
    try:
        i1 = RIOT_RANK_TIERS.index(t1)
        i2 = RIOT_RANK_TIERS.index(t2)
        return abs(i1 - i2) <= 1
    except ValueError:
        return t1 == t2


def compatibility_v2(a: dict, b: dict) -> dict:
    """Returns {score: 0-100, breakdown: {...}, shared_games: [...]}.

    Weights (per spec):
      Recently Played Games: 70% (1=40, 2=60, 3=70)
      Steam Library (top5):  15% (3+=15, 2=10, 1=5)
      Riot Bonus:             5% (same LoL game + similar rank)
      Schedule Overlap:      10% (any overlap)
    """
    a_recent = _ci_set(a.get("recently_played_games", []))
    b_recent = _ci_set(b.get("recently_played_games", []))
    recent_shared = a_recent & b_recent
    recent_count = len(recent_shared)
    if recent_count >= 3:
        recent_pts = 70
    elif recent_count == 2:
        recent_pts = 60
    elif recent_count == 1:
        recent_pts = 40
    else:
        recent_pts = 0

    a_top5 = _ci_set([g.get("name", "") for g in (a.get("top_games", []) or [])[:5]])
    b_top5 = _ci_set([g.get("name", "") for g in (b.get("top_games", []) or [])[:5]])
    top5_shared = a_top5 & b_top5
    top5_count = len(top5_shared)
    if top5_count >= 3:
        top5_pts = 15
    elif top5_count == 2:
        top5_pts = 10
    elif top5_count == 1:
        top5_pts = 5
    else:
        top5_pts = 0

    riot_pts = 0
    a_lol = a.get("lol_profile") or {}
    b_lol = b.get("lol_profile") or {}
    if a.get("riot_id") and b.get("riot_id"):
        a_tier = _rank_tier(a_lol.get("solo_rank")) or _rank_tier(a_lol.get("flex_rank"))
        b_tier = _rank_tier(b_lol.get("solo_rank")) or _rank_tier(b_lol.get("flex_rank"))
        if _tier_similar(a_tier, b_tier):
            riot_pts = 5

    a_slots = set(a.get("playtime_slots", []) or [])
    b_slots = set(b.get("playtime_slots", []) or [])
    schedule_pts = 10 if (a_slots & b_slots) else 0

    total = recent_pts + top5_pts + riot_pts + schedule_pts
    # Shared games for UI: combine recent + top5 (case-preserved)
    a_recent_orig = a.get("recently_played_games", []) or []
    b_recent_orig = set(g.lower() for g in (b.get("recently_played_games", []) or []))
    shared_display = [g for g in a_recent_orig if g.lower() in b_recent_orig]
    if not shared_display:
        a_top5_orig = [g.get("name", "") for g in (a.get("top_games", []) or [])[:5]]
        b_top5_orig = set(g.get("name", "").lower() for g in (b.get("top_games", []) or [])[:5])
        shared_display = [n for n in a_top5_orig if n and n.lower() in b_top5_orig]

    return {
        "score": min(100, max(0, total)),
        "breakdown": {
            "recently_played": recent_pts,
            "steam_library": top5_pts,
            "riot_bonus": riot_pts,
            "schedule": schedule_pts,
        },
        "shared_games": shared_display[:5],
    }


def priority_score(u: dict, viewer_recent: set, viewer_top5: set) -> int:
    """Lower = higher priority for sorting.
    0: currently playing the SAME game (in viewer's recent)
    1: currently playing any game
    2: most recent game matches viewer's recent (and recent within 24h)
    3: active within last 5min
    4: active within last 3h
    5: active within 24h
    6: active within 7 days
    7: inactive
    """
    cur = (u.get("current_steam_game") or {}).get("name") or ""
    if cur:
        if cur.lower() in viewer_recent or cur.lower() in viewer_top5:
            return 0
        return 1
    mrg = (u.get("most_recent_game") or "").lower()
    mrg_at = u.get("most_recent_game_at")
    if mrg and mrg_at:
        try:
            if (now() - datetime.fromisoformat(mrg_at)) < timedelta(hours=24):
                if mrg in viewer_recent or mrg in viewer_top5:
                    return 2
        except Exception:
            pass
    last = u.get("last_active")
    if last:
        try:
            delta = now() - datetime.fromisoformat(last)
            if delta < timedelta(minutes=5):
                return 3
            if delta < timedelta(hours=3):
                return 4
            if delta < timedelta(hours=24):
                return 5
            if delta < INACTIVE_THRESHOLD:
                return 6
        except Exception:
            pass
    return 7


# ---------- Steam current game refresh (60s TTL) ----------
async def refresh_steam_current_game(user: dict, force: bool = False) -> dict:
    """Refresh Steam current game with 60s cache. Updates user doc in-place."""
    steam_id = user.get("steam_id")
    if not steam_id:
        return user
    last_check = user.get("current_steam_game_updated_at")
    if not force and last_check:
        try:
            if (now() - datetime.fromisoformat(last_check)) < STEAM_CURRENT_GAME_TTL:
                return user
        except Exception:
            pass
    # Seeded users (or any without real Steam linking) can be marked do_not_refresh
    if user.get("steam_seeded"):
        # don't hit Steam API for fake seeds
        return user
    try:
        current = await fetch_steam_current_game(steam_id)
    except Exception:
        current = None
    updates = {"current_steam_game_updated_at": now().isoformat()}
    if current:
        updates["current_steam_game"] = current
        updates["most_recent_game"] = current.get("name")
        updates["most_recent_game_at"] = now().isoformat()
    else:
        updates["current_steam_game"] = None
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    user.update(updates)
    return user


# ---------- Inactive status & return bonus ----------
async def check_inactive_status(user: dict) -> dict:
    """Mark user inactive if last_active > 7 days. On return, grant bonus (once)."""
    last = user.get("last_active")
    if not last:
        return user
    try:
        delta = now() - datetime.fromisoformat(last)
    except Exception:
        return user
    was_inactive = bool(user.get("inactive_at"))
    is_currently_inactive = delta > INACTIVE_THRESHOLD
    updates = {}
    if is_currently_inactive and not was_inactive:
        updates["inactive_at"] = now().isoformat()
    elif not is_currently_inactive and was_inactive:
        # Return from inactive
        updates["inactive_at"] = None
        if not user.get("inactive_return_bonus_used"):
            updates["super_likes_remaining"] = (user.get("super_likes_remaining", 0) or 0) + 1
            updates["standout_boost_until"] = (now() + timedelta(hours=1)).isoformat()
            updates["inactive_return_bonus_used"] = True
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        user.update(updates)
    return user


# ---------- Compatibility scoring (v1 - legacy, kept for backward compat) ----------
def compatibility(a: dict, b: dict) -> dict:
    """Legacy v1 - now delegates to v2 for consistency."""
    return compatibility_v2(a, b)


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"message": "Gaming Buddy API"}


@api_router.post("/auth/signup")
async def signup(body: SignupBody):
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = str(uuid.uuid4())
    user_doc = {
        "id": uid,
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "username": body.username,
        "age": body.age,
        "country": body.country,
        "city": body.city or "",
        "languages": body.languages,
        "bio": body.bio,
        "profile_photo": body.profile_photo or f"https://api.dicebear.com/7.x/adventurer/png?seed={body.username}&backgroundColor=ff6a1a",
        "steam_avatar": None,
        "steam_profile_url": None,
        "top_games": [g.dict() for g in body.top_games],
        "recently_played_games": (body.recently_played_games or [])[:3],
        "playtime_slots": [s for s in (body.playtime_slots or []) if s in PLAYTIME_SLOTS][:2],
        "steam_total_hours": sum(int(g.hours) for g in body.top_games),
        "last_active": now().isoformat(),
        "daily_likes_used": 0,
        "super_likes_remaining": 1,
        "like_reset_at": (now() + timedelta(hours=24)).isoformat(),
        "super_like_reset_at": (now() + timedelta(days=7)).isoformat(),
        "onboarding_complete": False,
        "created_at": now().isoformat(),
    }
    await db.users.insert_one(user_doc.copy())
    token = secrets.token_urlsafe(32)
    await db.sessions.insert_one({"token": token, "user_id": uid, "created_at": now().isoformat()})
    return {"token": token, "user": me_user(user_doc)}


@api_router.post("/auth/login")
async def login(body: LoginBody):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not check_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    await db.sessions.insert_one({"token": token, "user_id": user["id"], "created_at": now().isoformat()})
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_active": now().isoformat()}})
    user["last_active"] = now().isoformat()
    user = await refresh_quotas(user)
    return {"token": token, "user": me_user(user)}


@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    user = await refresh_quotas(user)
    user = await check_inactive_status(user)
    user = await refresh_steam_current_game(user)
    return me_user(user)


@api_router.put("/profile/me")
async def update_profile(body: UpdateProfileBody, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if "top_games" in updates:
        updates["top_games"] = [g if isinstance(g, dict) else g.dict() for g in updates["top_games"]]
        updates["steam_total_hours"] = sum(int(g.get("hours", 0)) for g in updates["top_games"])
    if "recently_played_games" in updates:
        updates["recently_played_games"] = list(updates["recently_played_games"])[:3]
    if "playtime_slots" in updates:
        updates["playtime_slots"] = [s for s in updates["playtime_slots"] if s in PLAYTIME_SLOTS][:2]
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        user.update(updates)
    return me_user(user)


@api_router.get("/swipe/feed")
async def swipe_feed(user: dict = Depends(get_current_user)):
    user = await refresh_quotas(user)
    user = await check_inactive_status(user)
    user = await refresh_steam_current_game(user)
    swiped = await db.swipes.find({"user_id": user["id"]}, {"_id": 0, "target_user_id": 1}).to_list(10000)
    swiped_ids = {s["target_user_id"] for s in swiped}
    swiped_ids.add(user["id"])
    others = await db.users.find({
        "id": {"$nin": list(swiped_ids)},
        "is_banned": {"$ne": True},
    }, {"_id": 0, "password_hash": 0}).to_list(500)

    viewer_recent = _ci_set(user.get("recently_played_games", []))
    viewer_top5 = _ci_set([g.get("name", "") for g in (user.get("top_games", []) or [])[:5]])

    enriched = []
    inactive_pool = []
    for o in others:
        comp = compatibility_v2(user, o)
        p = public_user(o)
        p["match_percentage"] = comp["score"]
        p["shared_games"] = comp["shared_games"]
        p["compat_breakdown"] = comp["breakdown"]
        prio = priority_score(o, viewer_recent, viewer_top5)
        p["_prio"] = prio
        if prio >= 7 or p.get("is_inactive"):
            inactive_pool.append(p)
        else:
            enriched.append(p)

    # 50% filter: keep only >=50% if we have enough; otherwise relax
    above_50 = [c for c in enriched if c["match_percentage"] >= MIN_COMPAT_TO_SHOW]
    if len(above_50) >= 10:
        primary = above_50
    else:
        primary = enriched  # relax filter when pool is thin

    # Sort: priority asc (0=playing-same-game first) then match_percentage desc
    primary.sort(key=lambda c: (c["_prio"], -c["match_percentage"]))

    # If still nothing, append inactive pool at bottom
    if not primary:
        inactive_pool.sort(key=lambda c: -c["match_percentage"])
        primary = inactive_pool[:30]

    # Strip internal fields
    for c in primary:
        c.pop("_prio", None)

    return {
        "cards": primary,
        "daily_likes_used": user.get("daily_likes_used", 0),
        "daily_likes_limit": 20,
        "super_likes_remaining": user.get("super_likes_remaining", 0),
        "like_reset_at": user.get("like_reset_at"),
        "super_like_reset_at": user.get("super_like_reset_at"),
        "is_admin": bool(user.get("is_admin", False)),
    }


@api_router.post("/swipe")
async def swipe(body: SwipeBody, user: dict = Depends(get_current_user)):
    user = await refresh_quotas(user)
    if body.target_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot swipe self")
    target = await db.users.find_one({"id": body.target_user_id}, {"_id": 0, "password_hash": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Quota checks (admins bypass all limits)
    if not user.get("is_admin"):
        if body.action == "like":
            if user.get("daily_likes_used", 0) >= 20:
                raise HTTPException(status_code=429, detail="Daily like limit reached")
        if body.action == "superlike":
            if user.get("super_likes_remaining", 0) <= 0:
                raise HTTPException(status_code=429, detail="No super likes remaining")

    # Record swipe (upsert to avoid duplicates)
    await db.swipes.update_one(
        {"user_id": user["id"], "target_user_id": body.target_user_id},
        {"$set": {"action": body.action, "created_at": now().isoformat()}},
        upsert=True,
    )

    # Decrement quota (skip for admins)
    if not user.get("is_admin"):
        if body.action == "like":
            await db.users.update_one({"id": user["id"]}, {"$inc": {"daily_likes_used": 1}})
        if body.action == "superlike":
            await db.users.update_one({"id": user["id"]}, {"$inc": {"super_likes_remaining": -1}})

    # Match check: did target swipe like/superlike on us?
    matched = False
    match_id = None
    if body.action in ("like", "superlike"):
        their = await db.swipes.find_one({"user_id": body.target_user_id, "target_user_id": user["id"]})
        if their and their.get("action") in ("like", "superlike"):
            # Create match (if not exists)
            existing_match = await db.matches.find_one({
                "$or": [
                    {"user_a": user["id"], "user_b": body.target_user_id},
                    {"user_a": body.target_user_id, "user_b": user["id"]},
                ]
            }, {"_id": 0})
            if existing_match:
                match_id = existing_match["id"]
            else:
                match_id = str(uuid.uuid4())
                await db.matches.insert_one({
                    "id": match_id,
                    "user_a": user["id"],
                    "user_b": body.target_user_id,
                    "created_at": now().isoformat(),
                })
            matched = True

    return {
        "matched": matched,
        "match_id": match_id,
        "matched_user": public_user(target) if matched else None,
    }


@api_router.get("/standout")
async def standout(user: dict = Depends(get_current_user)):
    user = await refresh_steam_current_game(user)
    swiped = await db.swipes.find({"user_id": user["id"]}, {"_id": 0, "target_user_id": 1}).to_list(10000)
    swiped_ids = {s["target_user_id"] for s in swiped}
    swiped_ids.add(user["id"])
    others = await db.users.find({
        "id": {"$nin": list(swiped_ids)},
        "is_banned": {"$ne": True},
    }, {"_id": 0, "password_hash": 0}).to_list(500)
    enriched = []
    viewer_recent = _ci_set(user.get("recently_played_games", []))
    viewer_top5 = _ci_set([g.get("name", "") for g in (user.get("top_games", []) or [])[:5]])
    for o in others:
        comp = compatibility_v2(user, o)
        if comp["score"] < MIN_COMPAT_TO_SHOW:
            continue
        p = public_user(o)
        p["match_percentage"] = comp["score"]
        p["shared_games"] = comp["shared_games"]
        p["compat_breakdown"] = comp["breakdown"]
        # Apply 1h Standout Boost if other user has it
        boost_until = o.get("standout_boost_until")
        boost_active = False
        if boost_until:
            try:
                boost_active = now() < datetime.fromisoformat(boost_until)
            except Exception:
                boost_active = False
        p["boost_active"] = boost_active
        p["_prio"] = priority_score(o, viewer_recent, viewer_top5)
        enriched.append(p)
    # Sort: boost first, then by priority, then by score desc
    enriched.sort(key=lambda c: (0 if c["boost_active"] else 1, c["_prio"], -c["match_percentage"]))
    for c in enriched:
        c.pop("_prio", None)
    return {"profiles": enriched[:10]}


@api_router.get("/home/activity")
async def home_activity(user: dict = Depends(get_current_user)):
    """Live game-activity card data for the Home screen + auto-matchmaking."""
    user = await refresh_steam_current_game(user)
    cur = (user.get("current_steam_game") or {}).get("name")
    last_game = user.get("most_recent_game")
    last_game_at = user.get("most_recent_game_at")
    recent = user.get("recently_played_games", []) or []
    top = [g.get("name") for g in (user.get("top_games") or []) if g.get("name")]
    focus = cur or last_game or (recent[0] if recent else (top[0] if top else None))
    focus_l = (focus or "").lower()

    swiped = await db.swipes.find({"user_id": user["id"]}, {"_id": 0, "target_user_id": 1}).to_list(10000)
    swiped_ids = {s["target_user_id"] for s in swiped}
    swiped_ids.add(user["id"])
    others = await db.users.find({
        "id": {"$nin": list(swiped_ids)},
        "is_banned": {"$ne": True},
    }, {"_id": 0, "password_hash": 0}).to_list(1000)

    same_game_count = 0
    pool = 0
    for o in others:
        pool += 1
        if not focus_l:
            continue
        o_games = {g.lower() for g in (o.get("recently_played_games") or [])}
        o_top = {(g.get("name") or "").lower() for g in (o.get("top_games") or [])}
        o_cur = ((o.get("current_steam_game") or {}).get("name") or "").lower()
        active = _is_active_recently(o.get("last_active"))
        if (focus_l and focus_l == o_cur) or ((focus_l in o_games or focus_l in o_top) and active):
            same_game_count += 1

    return {
        "focus_game": focus,
        "is_playing_now": bool(cur),
        "last_game": last_game,
        "last_game_at": last_game_at,
        "active_same_game_count": same_game_count,
        "matchmaking_pool": pool,
    }


@api_router.get("/matches")
async def list_matches(user: dict = Depends(get_current_user)):
    matches = await db.matches.find({
        "$or": [{"user_a": user["id"]}, {"user_b": user["id"]}]
    }, {"_id": 0}).sort("created_at", -1).to_list(200)
    result = []
    for m in matches:
        other_id = m["user_b"] if m["user_a"] == user["id"] else m["user_a"]
        other = await db.users.find_one({"id": other_id}, {"_id": 0, "password_hash": 0})
        if not other:
            continue
        last_msg = await db.messages.find_one(
            {"match_id": m["id"]}, {"_id": 0}, sort=[("created_at", -1)]
        )
        result.append({
            "match_id": m["id"],
            "user": public_user(other),
            "last_message": last_msg["text"] if last_msg else None,
            "last_message_at": last_msg["created_at"] if last_msg else None,
            "created_at": m["created_at"],
        })
    return {"matches": result}


@api_router.get("/messages/{match_id}")
async def get_messages(match_id: str, user: dict = Depends(get_current_user)):
    match = await db.matches.find_one({"id": match_id}, {"_id": 0})
    if not match or user["id"] not in (match["user_a"], match["user_b"]):
        raise HTTPException(status_code=404, detail="Match not found")
    msgs = await db.messages.find({"match_id": match_id}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    other_id = match["user_b"] if match["user_a"] == user["id"] else match["user_a"]
    other = await db.users.find_one({"id": other_id}, {"_id": 0, "password_hash": 0})
    return {
        "messages": msgs,
        "other_user": public_user(other) if other else None,
    }


@api_router.post("/messages/{match_id}")
async def send_message(match_id: str, body: MessageBody, user: dict = Depends(get_current_user)):
    match = await db.matches.find_one({"id": match_id}, {"_id": 0})
    if not match or user["id"] not in (match["user_a"], match["user_b"]):
        raise HTTPException(status_code=404, detail="Match not found")
    msg = {
        "id": str(uuid.uuid4()),
        "match_id": match_id,
        "sender_id": user["id"],
        "text": body.text,
        "created_at": now().isoformat(),
    }
    await db.messages.insert_one(msg.copy())
    return msg


# ---------- Seed data ----------
SEED_USERS = [
    {"username": "NovaStrike", "age": 22, "country": "USA", "languages": ["English"],
     "bio": "Looking for chill Valorant teammates. Diamond rank, mic always on.",
     "photo": "https://images.pexels.com/photos/9071735/pexels-photo-9071735.jpeg",
     "games": [{"name": "Valorant", "hours": 1200}, {"name": "CS2", "hours": 850}, {"name": "Apex Legends", "hours": 340}]},
    {"username": "PixelPanda", "age": 24, "country": "Canada", "languages": ["English", "French"],
     "bio": "Casual gamer who plays for fun. Love co-op games and survival sims.",
     "photo": "https://images.pexels.com/photos/34179709/pexels-photo-34179709.jpeg",
     "games": [{"name": "Rust", "hours": 620}, {"name": "Valheim", "hours": 280}, {"name": "Terraria", "hours": 180}]},
    {"username": "GhostByte", "age": 26, "country": "UK", "languages": ["English"],
     "bio": "FPS enjoyer. CS2 main, also grinding Tarkov. Down for ranked.",
     "photo": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6",
     "games": [{"name": "CS2", "hours": 1850}, {"name": "Escape from Tarkov", "hours": 720}, {"name": "Valorant", "hours": 200}]},
    {"username": "LunaQuest", "age": 23, "country": "Germany", "languages": ["German", "English"],
     "bio": "RPG addict. Currently obsessed with Baldur's Gate 3. ESO since beta.",
     "photo": "https://images.unsplash.com/photo-1530651788726-1dbf58eeef1f",
     "games": [{"name": "Baldur's Gate 3", "hours": 410}, {"name": "Elder Scrolls Online", "hours": 1100}, {"name": "Skyrim", "hours": 680}]},
    {"username": "ZeroCool", "age": 21, "country": "USA", "languages": ["English", "Spanish"],
     "bio": "Apex predator badge. LF duo for ranked grinding. No toxic energy.",
     "photo": "https://images.pexels.com/photos/9071724/pexels-photo-9071724.jpeg",
     "games": [{"name": "Apex Legends", "hours": 2100}, {"name": "Valorant", "hours": 420}, {"name": "Fortnite", "hours": 300}]},
    {"username": "VoidWalker", "age": 27, "country": "Australia", "languages": ["English"],
     "bio": "Destiny 2 raid lead. Need 5 more for weekly clears. Sherpa-friendly.",
     "photo": "https://images.unsplash.com/photo-1568602471122-7832951cc4c5",
     "games": [{"name": "Destiny 2", "hours": 3400}, {"name": "Warframe", "hours": 1200}, {"name": "Path of Exile", "hours": 600}]},
    {"username": "NeonKitsune", "age": 25, "country": "Japan", "languages": ["Japanese", "English"],
     "bio": "FFXIV raider on Mana DC. Also play fighting games. Mains Jamie in SF6.",
     "photo": "https://images.unsplash.com/photo-1494790108377-be9c29b29330",
     "games": [{"name": "Final Fantasy XIV", "hours": 2800}, {"name": "Street Fighter 6", "hours": 540}, {"name": "Genshin Impact", "hours": 980}]},
    {"username": "ArcadeRex", "age": 29, "country": "USA", "languages": ["English"],
     "bio": "Old school gamer. Rocket League diamond. Always down for casual 2s.",
     "photo": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d",
     "games": [{"name": "Rocket League", "hours": 1600}, {"name": "CS2", "hours": 420}, {"name": "Dota 2", "hours": 1100}]},
    {"username": "FrostByte", "age": 20, "country": "Sweden", "languages": ["Swedish", "English"],
     "bio": "LoL Diamond ADC. Looking for support duo. EUW server.",
     "photo": "https://images.unsplash.com/photo-1463453091185-61582044d556",
     "games": [{"name": "League of Legends", "hours": 2400}, {"name": "Teamfight Tactics", "hours": 380}, {"name": "Valorant", "hours": 220}]},
    {"username": "SilentMage", "age": 24, "country": "Brazil", "languages": ["Portuguese", "English"],
     "bio": "MMO veteran. WoW since Vanilla. Currently raiding Mythic in Dragonflight.",
     "photo": "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce",
     "games": [{"name": "World of Warcraft", "hours": 5200}, {"name": "Final Fantasy XIV", "hours": 800}, {"name": "Lost Ark", "hours": 600}]},
    {"username": "CyberFox", "age": 22, "country": "South Korea", "languages": ["Korean", "English"],
     "bio": "Valorant Immortal. Also play Overwatch 2 comp. Looking for English speakers.",
     "photo": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e",
     "games": [{"name": "Valorant", "hours": 2200}, {"name": "Overwatch 2", "hours": 980}, {"name": "League of Legends", "hours": 1100}]},
    {"username": "EmberDrake", "age": 28, "country": "France", "languages": ["French", "English"],
     "bio": "Souls-like enthusiast. Elden Ring 100%. Looking for co-op invasion partners.",
     "photo": "https://images.unsplash.com/photo-1546961342-1c97cb0659db",
     "games": [{"name": "Elden Ring", "hours": 720}, {"name": "Dark Souls 3", "hours": 480}, {"name": "Sekiro", "hours": 220}]},
    {"username": "BoltStream", "age": 23, "country": "Netherlands", "languages": ["Dutch", "English"],
     "bio": "Streamer chasing affiliate. Variety gamer. Hop in chat sometime!",
     "photo": "https://images.unsplash.com/photo-1531123897727-8f129e1688ce",
     "games": [{"name": "Minecraft", "hours": 1800}, {"name": "Among Us", "hours": 300}, {"name": "Fall Guys", "hours": 200}]},
    {"username": "ShadowLynx", "age": 26, "country": "Russia", "languages": ["Russian", "English"],
     "bio": "Tarkov main. Looking for squad mates who don't rage at deaths.",
     "photo": "https://images.unsplash.com/photo-1521119989659-a83eee488004",
     "games": [{"name": "Escape from Tarkov", "hours": 1900}, {"name": "DayZ", "hours": 680}, {"name": "Hunt: Showdown", "hours": 420}]},
    {"username": "MochiPaws", "age": 21, "country": "USA", "languages": ["English"],
     "bio": "Cozy gamer. Stardew Valley, Animal Crossing, Hollow Knight vibes.",
     "photo": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2",
     "games": [{"name": "Stardew Valley", "hours": 480}, {"name": "Hollow Knight", "hours": 220}, {"name": "Terraria", "hours": 380}]},
    {"username": "RiotBeam", "age": 25, "country": "USA", "languages": ["English"],
     "bio": "Overwatch 2 GM support main. Looking for tank duo.",
     "photo": "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453",
     "games": [{"name": "Overwatch 2", "hours": 2700}, {"name": "Apex Legends", "hours": 380}, {"name": "Valorant", "hours": 220}]},
    {"username": "JadeKnight", "age": 27, "country": "China", "languages": ["Mandarin", "English"],
     "bio": "Genshin AR60. Also play Honkai Star Rail and ZZZ. Co-op friendly.",
     "photo": "https://images.unsplash.com/photo-1488161628813-04466f872be2",
     "games": [{"name": "Genshin Impact", "hours": 1800}, {"name": "Honkai Star Rail", "hours": 720}, {"name": "Zenless Zone Zero", "hours": 200}]},
    {"username": "TitanCrash", "age": 30, "country": "USA", "languages": ["English"],
     "bio": "Dota 2 6k MMR. Support player. EU East/US East servers.",
     "photo": "https://images.unsplash.com/photo-1499996860823-5214fcc65f8f",
     "games": [{"name": "Dota 2", "hours": 4200}, {"name": "CS2", "hours": 600}, {"name": "Path of Exile", "hours": 800}]},
    {"username": "PixieDust", "age": 22, "country": "Mexico", "languages": ["Spanish", "English"],
     "bio": "Sims 4 obsessed. Also love narrative games like Life is Strange.",
     "photo": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80",
     "games": [{"name": "The Sims 4", "hours": 920}, {"name": "Life is Strange", "hours": 80}, {"name": "Stardew Valley", "hours": 220}]},
    {"username": "RogueWave", "age": 24, "country": "USA", "languages": ["English"],
     "bio": "FPS junkie. Apex, Valorant, CS2. Discord active, mic always on.",
     "photo": "https://images.unsplash.com/photo-1507591064344-4c6ce005b128",
     "games": [{"name": "Apex Legends", "hours": 1400}, {"name": "Valorant", "hours": 900}, {"name": "CS2", "hours": 720}]},
]


def _seed_recent_games(s: dict) -> List[str]:
    """Top 2-3 game names act as the user's recently played games."""
    names = [g.get("name", "") for g in s.get("games", []) if g.get("name")]
    # deterministic 2 or 3 based on username
    take = 3 if (hash(s["username"]) % 2 == 0) else 2
    return names[:take]


def _seed_playtime_slots(s: dict) -> List[str]:
    """Assign 2 deterministic slots, biased toward evening for natural overlap."""
    h = abs(hash("slot-" + s["username"]))
    # Always include a common prime-time slot so seed users share schedules
    evening = "18:00-21:00" if (h % 2 == 0) else "21:00-00:00"
    second = PLAYTIME_SLOTS[h % len(PLAYTIME_SLOTS)]
    slots = [evening]
    if second != evening:
        slots.append(second)
    return slots


async def seed_users():
    for s in SEED_USERS:
        existing = await db.users.find_one({"username": s["username"]})
        recent = _seed_recent_games(s)
        slots = _seed_playtime_slots(s)
        if existing:
            # Backfill missing compatibility fields on previously seeded docs
            patch = {}
            if not existing.get("recently_played_games"):
                patch["recently_played_games"] = recent
            if not existing.get("playtime_slots"):
                patch["playtime_slots"] = slots
            if not existing.get("onboarding_complete"):
                patch["onboarding_complete"] = True
            if patch:
                await db.users.update_one({"_id": existing["_id"]}, {"$set": patch})
            continue
        uid = str(uuid.uuid4())
        # Stagger last_active times for variety
        offset_mins = (hash(s["username"]) % 360)
        last_active = (now() - timedelta(minutes=offset_mins)).isoformat()
        doc = {
            "id": uid,
            "email": f"{s['username'].lower()}@seed.gamingbuddy.app",
            "password_hash": hash_password("seedpass123"),
            "username": s["username"],
            "age": s["age"],
            "country": s["country"],
            "languages": s["languages"],
            "bio": s["bio"],
            "profile_photo": s["photo"],
            "steam_avatar": s["photo"],
            "steam_profile_url": f"https://steamcommunity.com/id/{s['username'].lower()}",
            "top_games": s["games"],
            "recently_played_games": recent,
            "playtime_slots": slots,
            "onboarding_complete": True,
            "last_active": last_active,
            "daily_likes_used": 0,
            "super_likes_remaining": 1,
            "like_reset_at": (now() + timedelta(hours=24)).isoformat(),
            "super_like_reset_at": (now() + timedelta(days=7)).isoformat(),
            "is_seed": True,
            "created_at": now().isoformat(),
        }
        await db.users.insert_one(doc)


@app.on_event("startup")
async def on_startup():
    await seed_admin()
    await seed_users()
    # Preload Riot Data Dragon champion mapping (non-blocking on failure)
    try:
        await load_champion_mapping()
    except Exception:
        pass


async def seed_admin():
    """Ensure a primary admin account exists with full privileges."""
    admin_email = "admin@gaminder.app"
    existing = await db.users.find_one({"email": admin_email})
    admin_password_hash = hash_password("Gaminder@2025!")
    if existing:
        # keep is_admin flag and refresh quota fields (idempotent)
        patch = {
            "is_admin": True,
            "password_hash": admin_password_hash,
            "daily_likes_used": 0,
            "super_likes_remaining": 99,
        }
        if not existing.get("recently_played_games"):
            patch["recently_played_games"] = ["Valorant", "League of Legends", "CS2"]
        if not existing.get("playtime_slots"):
            patch["playtime_slots"] = ["18:00-21:00", "21:00-00:00"]
        patch["onboarding_complete"] = True
        await db.users.update_one({"email": admin_email}, {"$set": patch})
        return
    uid = str(uuid.uuid4())
    await db.users.insert_one({
        "id": uid,
        "email": admin_email,
        "password_hash": admin_password_hash,
        "username": "Admin",
        "age": 28,
        "country": "Turkey",
        "languages": ["English", "Turkish"],
        "bio": "Gaminder admin \u2014 has full access for testing and moderation.",
        "profile_photo": "https://api.dicebear.com/7.x/adventurer/png?seed=admin&backgroundColor=ff6a1a",
        "top_games": [
            {"name": "Valorant", "hours": 0},
            {"name": "League of Legends", "hours": 0},
            {"name": "CS2", "hours": 0},
        ],
        "last_active": now().isoformat(),
        "daily_likes_used": 0,
        "super_likes_remaining": 99,
        "like_reset_at": (now() + timedelta(hours=24)).isoformat(),
        "super_like_reset_at": (now() + timedelta(days=365)).isoformat(),
        "is_admin": True,
        "is_seed": False,
        "onboarding_complete": True,
        "created_at": now().isoformat(),
    })


# ============================================================================
# Steam linking endpoints
# ============================================================================
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "")


@api_router.get("/steam/auth-url")
async def steam_auth_url(redirect_uri: str, user: dict = Depends(get_current_user)):
    if not PUBLIC_BASE_URL:
        raise HTTPException(status_code=500, detail="PUBLIC_BASE_URL not configured")
    # Use a one-time link nonce stored server-side instead of bearer token in state
    nonce = secrets.token_urlsafe(24)
    await db.steam_link_nonces.insert_one({
        "nonce": nonce,
        "user_id": user["id"],
        "redirect_uri": redirect_uri,
        "created_at": now().isoformat(),
    })
    callback_url = (
        f"{PUBLIC_BASE_URL}/api/steam/callback?nonce={quote(nonce)}"
    )
    realm = PUBLIC_BASE_URL
    auth_url = build_steam_openid_url(callback_url, realm)
    return {"auth_url": auth_url}


@api_router.get("/steam/callback")
async def steam_callback(request: Request):
    params = dict(request.query_params)
    nonce = params.get("nonce")
    if not nonce:
        raise HTTPException(status_code=400, detail="Missing nonce")
    link_rec = await db.steam_link_nonces.find_one_and_delete({"nonce": nonce})
    if not link_rec:
        raise HTTPException(status_code=400, detail="Invalid or expired link nonce")

    steam_id = await verify_steam_openid(params)
    redirect_uri = link_rec.get("redirect_uri") or "/"
    sep = "&" if "?" in redirect_uri else "?"
    if not steam_id:
        return RedirectResponse(url=f"{redirect_uri}{sep}status=error&reason=verify_failed", status_code=302)

    profile_data, top_games, profile_private = await fetch_steam_profile_and_games(steam_id)

    update_doc = {
        "steam_id": steam_id,
        "steam_avatar": profile_data.get("avatarfull") or profile_data.get("avatar"),
        "steam_profile_url": profile_data.get("profileurl"),
        "steam_persona_name": profile_data.get("personaname"),
        "steam_profile_private": profile_private,
        "steam_linked_at": now().isoformat(),
        "onboarding_complete": True,
    }
    if top_games:
        # Replace top_games with Steam library
        update_doc["top_games"] = [{"name": g["name"], "hours": int(g["hours"])} for g in top_games]
    await db.users.update_one({"id": link_rec["user_id"]}, {"$set": update_doc})

    qparts = ["status=success"]
    if profile_private:
        qparts.append("profile_private=1")
    return RedirectResponse(url=f"{redirect_uri}{sep}{'&'.join(qparts)}", status_code=302)


# ============================================================================
# Riot linking endpoints
# ============================================================================
class RiotLinkBody(BaseModel):
    riot_id: str
    platform: str


@api_router.post("/riot/link")
async def riot_link(body: RiotLinkBody, user: dict = Depends(get_current_user)):
    try:
        profile = await fetch_riot_lol_profile(body.riot_id, body.platform)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch Riot data")

    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "riot_id": profile["riot_id"],
            "riot_platform": profile["platform"],
            "riot_puuid": profile["puuid"],
            "lol_profile": {
                "summoner_level": profile["summoner_level"],
                "solo_rank": profile["solo_rank"],
                "flex_rank": profile["flex_rank"],
                "top_champions": profile["top_champions"],
            },
            "riot_linked_at": now().isoformat(),
        }},
    )
    return {"riot_id": profile["riot_id"], "lol_profile": profile}


@api_router.post("/riot/unlink")
async def riot_unlink(user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"id": user["id"]},
        {"$unset": {"riot_id": "", "riot_platform": "", "riot_puuid": "", "lol_profile": "", "riot_linked_at": ""}},
    )
    return {"ok": True}


@api_router.post("/steam/unlink")
async def steam_unlink(user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"id": user["id"]},
        {"$unset": {"steam_id": "", "steam_avatar": "", "steam_profile_url": "", "steam_persona_name": "", "steam_profile_private": "", "steam_linked_at": ""}},
    )
    return {"ok": True}


# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

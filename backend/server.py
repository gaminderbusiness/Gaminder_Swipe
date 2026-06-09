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


# ---------- Models ----------
class Game(BaseModel):
    name: str
    hours: int


class UserPublic(BaseModel):
    id: str
    username: str
    age: int
    country: str
    languages: List[str]
    bio: str
    profile_photo: str
    steam_avatar: Optional[str] = None
    steam_profile_url: Optional[str] = None
    top_games: List[Game] = []
    last_active: Optional[str] = None
    activity_status: Literal["online", "away", "offline"] = "offline"


class UserMe(UserPublic):
    email: str
    daily_likes_used: int = 0
    super_likes_remaining: int = 1
    like_reset_at: Optional[str] = None
    super_like_reset_at: Optional[str] = None


class SignupBody(BaseModel):
    email: EmailStr
    password: str
    username: str
    age: int
    country: str
    languages: List[str]
    bio: str = ""
    profile_photo: str = ""
    top_games: List[Game] = []


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileBody(BaseModel):
    username: Optional[str] = None
    age: Optional[int] = None
    country: Optional[str] = None
    languages: Optional[List[str]] = None
    bio: Optional[str] = None
    profile_photo: Optional[str] = None
    top_games: Optional[List[Game]] = None


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
    return {
        "id": u["id"],
        "username": u["username"],
        "age": u["age"],
        "country": u["country"],
        "languages": u.get("languages", []),
        "bio": u.get("bio", ""),
        "profile_photo": u.get("profile_photo", ""),
        "steam_avatar": u.get("steam_avatar"),
        "steam_profile_url": u.get("steam_profile_url"),
        "steam_persona_name": u.get("steam_persona_name"),
        "steam_linked": bool(u.get("steam_id")),
        "top_games": u.get("top_games", []),
        "riot_id": u.get("riot_id"),
        "riot_platform": u.get("riot_platform"),
        "lol_profile": u.get("lol_profile"),
        "last_active": last,
        "activity_status": compute_activity(last),
    }


def me_user(u: dict) -> dict:
    base = public_user(u)
    base.update({
        "email": u["email"],
        "daily_likes_used": u.get("daily_likes_used", 0),
        "super_likes_remaining": u.get("super_likes_remaining", 1),
        "like_reset_at": u.get("like_reset_at"),
        "super_like_reset_at": u.get("super_like_reset_at"),
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


# ---------- Compatibility scoring ----------
def compatibility(a: dict, b: dict) -> dict:
    a_games = {g["name"]: g["hours"] for g in a.get("top_games", [])}
    b_games = {g["name"]: g["hours"] for g in b.get("top_games", [])}
    shared = list(set(a_games.keys()) & set(b_games.keys()))

    # Shared games (max 50)
    game_score = min(50, len(shared) * 18)
    # Playtime similarity (max 20)
    pt_score = 0
    if shared:
        diffs = []
        for g in shared:
            ah = a_games[g]
            bh = b_games[g]
            denom = max(ah, bh, 1)
            diffs.append(1 - abs(ah - bh) / denom)
        pt_score = int(20 * (sum(diffs) / len(diffs)))
    # Country (max 15)
    country_score = 15 if a.get("country") and a.get("country") == b.get("country") else 0
    # Language (max 15)
    common_langs = set(a.get("languages", [])) & set(b.get("languages", []))
    lang_score = 15 if common_langs else 0

    base = game_score + pt_score + country_score + lang_score
    # Add a small deterministic boost so cards aren't all 0% if no overlap
    if base < 30:
        # seed boost from id hash
        boost = (abs(hash(a["id"] + b["id"])) % 25) + 10
        base = max(base, boost)
    return {"score": min(99, max(1, base)), "shared_games": shared}


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
        "languages": body.languages,
        "bio": body.bio,
        "profile_photo": body.profile_photo or f"https://api.dicebear.com/7.x/adventurer/png?seed={body.username}",
        "steam_avatar": body.profile_photo or None,
        "steam_profile_url": f"https://steamcommunity.com/id/{body.username.lower()}",
        "top_games": [g.dict() for g in body.top_games],
        "last_active": now().isoformat(),
        "daily_likes_used": 0,
        "super_likes_remaining": 1,
        "like_reset_at": (now() + timedelta(hours=24)).isoformat(),
        "super_like_reset_at": (now() + timedelta(days=7)).isoformat(),
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
    return me_user(user)


@api_router.put("/profile/me")
async def update_profile(body: UpdateProfileBody, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if "top_games" in updates:
        updates["top_games"] = [g if isinstance(g, dict) else g.dict() for g in updates["top_games"]]
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        user.update(updates)
    return me_user(user)


@api_router.get("/swipe/feed")
async def swipe_feed(user: dict = Depends(get_current_user)):
    user = await refresh_quotas(user)
    swiped = await db.swipes.find({"user_id": user["id"]}, {"_id": 0, "target_user_id": 1}).to_list(10000)
    swiped_ids = {s["target_user_id"] for s in swiped}
    swiped_ids.add(user["id"])
    others = await db.users.find({"id": {"$nin": list(swiped_ids)}}, {"_id": 0, "password_hash": 0}).to_list(200)
    cards = []
    for o in others:
        comp = compatibility(user, o)
        p = public_user(o)
        p["match_percentage"] = comp["score"]
        p["shared_games"] = comp["shared_games"]
        cards.append(p)
    cards.sort(key=lambda c: c["match_percentage"], reverse=True)
    return {
        "cards": cards,
        "daily_likes_used": user.get("daily_likes_used", 0),
        "daily_likes_limit": 20,
        "super_likes_remaining": user.get("super_likes_remaining", 0),
        "like_reset_at": user.get("like_reset_at"),
        "super_like_reset_at": user.get("super_like_reset_at"),
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
    swiped = await db.swipes.find({"user_id": user["id"]}, {"_id": 0, "target_user_id": 1}).to_list(10000)
    swiped_ids = {s["target_user_id"] for s in swiped}
    swiped_ids.add(user["id"])
    others = await db.users.find({"id": {"$nin": list(swiped_ids)}}, {"_id": 0, "password_hash": 0}).to_list(200)
    enriched = []
    for o in others:
        comp = compatibility(user, o)
        p = public_user(o)
        p["match_percentage"] = comp["score"]
        p["shared_games"] = comp["shared_games"]
        enriched.append(p)
    # Top by match%, then by activity
    enriched.sort(key=lambda c: (c["match_percentage"], 0 if c["activity_status"] == "online" else 1), reverse=True)
    return {"profiles": enriched[:10]}


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


async def seed_users():
    count = await db.users.count_documents({"is_seed": True})
    if count >= len(SEED_USERS):
        return
    for s in SEED_USERS:
        existing = await db.users.find_one({"username": s["username"]})
        if existing:
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
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {
                "is_admin": True,
                "password_hash": admin_password_hash,
                "daily_likes_used": 0,
                "super_likes_remaining": 99,
            }},
        )
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

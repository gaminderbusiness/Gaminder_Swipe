"""Steam OpenID + Steam Web API + Riot Games API integration helpers."""
from __future__ import annotations

import os
import re
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlencode, quote

import httpx

STEAM_OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
STEAM_API_BASE = "https://api.steampowered.com"
DD_BASE = "https://ddragon.leagueoflegends.com"


def _steam_key() -> str:
    return os.environ.get("STEAM_API_KEY", "")


def _riot_key() -> str:
    return os.environ.get("RIOT_API_KEY", "")

_STEAM_ID_RE = re.compile(r"https?://steamcommunity\.com/openid/id/(\d+)")


# ============================================================================
# Steam
# ============================================================================
def build_steam_openid_url(callback_url: str, realm: str) -> str:
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": callback_url,
        "openid.realm": realm,
        "openid.ns.sreg": "http://openid.net/extensions/sreg/1.1",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return f"{STEAM_OPENID_ENDPOINT}?{urlencode(params)}"


async def verify_steam_openid(query_params: Dict[str, str]) -> Optional[str]:
    """Returns SteamID64 if response valid, else None."""
    claimed = query_params.get("openid.claimed_id", "")
    m = _STEAM_ID_RE.match(claimed)
    if not m:
        return None
    steam_id = m.group(1)

    verify_params = dict(query_params)
    verify_params["openid.mode"] = "check_authentication"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(STEAM_OPENID_ENDPOINT, data=verify_params)
    if resp.status_code != 200:
        return None
    if "is_valid:true" not in resp.text:
        return None
    return steam_id


async def fetch_steam_profile_and_games(steam_id: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], bool]:
    """Returns (player_summary, top_games_list[{name,hours,appid}], profile_private)."""
    profile_data: Dict[str, Any] = {}
    top_games: List[Dict[str, Any]] = []
    profile_private = False

    async with httpx.AsyncClient(base_url=STEAM_API_BASE, timeout=10.0) as client:
        try:
            r = await client.get(
                "/ISteamUser/GetPlayerSummaries/v2/",
                params={"key": _steam_key(), "steamids": steam_id},
            )
            r.raise_for_status()
            players = r.json().get("response", {}).get("players", [])
            if players:
                profile_data = players[0]
        except Exception:
            pass

        try:
            r = await client.get(
                "/IPlayerService/GetOwnedGames/v1/",
                params={
                    "key": _steam_key(),
                    "steamid": steam_id,
                    "include_appinfo": 1,
                    "include_played_free_games": 1,
                },
            )
            r.raise_for_status()
            games = r.json().get("response", {}).get("games", [])
            if not games:
                profile_private = True
            else:
                games.sort(key=lambda g: g.get("playtime_forever", 0), reverse=True)
                for g in games[:5]:
                    minutes = g.get("playtime_forever", 0)
                    hours = round(minutes / 60.0, 1)
                    name = g.get("name") or f"App {g.get('appid')}"
                    top_games.append({"appid": g.get("appid"), "name": name, "hours": hours})
        except Exception:
            profile_private = True

    return profile_data, top_games, profile_private


# ============================================================================
# Riot
# ============================================================================
PLATFORM_TO_REGION = {
    "NA1": "americas", "BR1": "americas", "LA1": "americas", "LA2": "americas",
    "EUW1": "europe", "EUN1": "europe", "TR1": "europe", "RU": "europe", "ME1": "europe",
    "KR": "asia", "JP1": "asia",
    "OC1": "sea", "PH2": "sea", "SG2": "sea", "TH2": "sea", "TW2": "sea", "VN2": "sea",
}


def platform_host(platform: str) -> str:
    return f"{platform.lower()}.api.riotgames.com"


def region_host(platform: str) -> Optional[str]:
    reg = PLATFORM_TO_REGION.get(platform.upper())
    if not reg:
        return None
    return f"{reg}.api.riotgames.com"


_CHAMP_MAP: Dict[int, str] = {}


async def load_champion_mapping() -> Dict[int, str]:
    global _CHAMP_MAP
    if _CHAMP_MAP:
        return _CHAMP_MAP
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            v = await client.get(f"{DD_BASE}/api/versions.json")
            v.raise_for_status()
            versions = v.json()
            latest = versions[0]
            c = await client.get(f"{DD_BASE}/cdn/{latest}/data/en_US/champion.json")
            c.raise_for_status()
            data = c.json().get("data", {})
            mapping: Dict[int, str] = {}
            for champ_name, champ_data in data.items():
                try:
                    key_int = int(champ_data["key"])
                    mapping[key_int] = champ_data.get("name", champ_name)
                except Exception:
                    continue
            _CHAMP_MAP = mapping
    except Exception:
        _CHAMP_MAP = {}
    return _CHAMP_MAP


async def _riot_get(client: httpx.AsyncClient, url: str) -> Optional[Any]:
    headers = {"X-Riot-Token": _riot_key()}
    r = await client.get(url, headers=headers, timeout=10.0)
    if r.status_code == 404:
        return None
    if r.status_code == 429:
        raise RuntimeError("Riot API rate limit hit. Try again in a few seconds.")
    if r.status_code == 401 or r.status_code == 403:
        raise RuntimeError("Riot API key invalid or expired (dev keys expire every 24h).")
    if r.status_code >= 500:
        raise RuntimeError("Riot servers are temporarily unavailable.")
    r.raise_for_status()
    return r.json()


async def fetch_riot_lol_profile(
    riot_id: str, platform: str
) -> Dict[str, Any]:
    """Returns enriched LoL profile dict or raises RuntimeError with user-friendly msg."""
    if "#" not in riot_id:
        raise RuntimeError("Riot ID must be in the format gameName#tagLine")
    game_name, tag_line = riot_id.split("#", 1)
    game_name = game_name.strip()
    tag_line = tag_line.strip()

    platform = platform.upper()
    rhost = region_host(platform)
    if not rhost:
        raise RuntimeError(f"Unknown platform: {platform}")
    phost = platform_host(platform)

    champ_map = await load_champion_mapping()

    async with httpx.AsyncClient() as client:
        # 1. Resolve PUUID via account-v1
        account = await _riot_get(
            client,
            f"https://{rhost}/riot/account/v1/accounts/by-riot-id/{quote(game_name)}/{quote(tag_line)}",
        )
        if not account or "puuid" not in account:
            raise RuntimeError(f"Riot account '{riot_id}' not found in {platform}")
        puuid = account["puuid"]
        canonical_riot_id = f"{account.get('gameName', game_name)}#{account.get('tagLine', tag_line)}"

        # 2. Summoner level via summoner-v4
        summoner = await _riot_get(
            client, f"https://{phost}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        )
        summoner_level = summoner.get("summonerLevel", 0) if summoner else 0
        summoner_id = summoner.get("id") if summoner else None

        # 3. Ranked entries by PUUID
        solo = None
        flex = None
        try:
            entries = await _riot_get(
                client, f"https://{phost}/lol/league/v4/entries/by-puuid/{puuid}"
            )
            if isinstance(entries, list):
                for e in entries:
                    summary = {
                        "queue_type": e.get("queueType", ""),
                        "tier": e.get("tier", "UNRANKED"),
                        "division": e.get("rank", ""),
                        "league_points": e.get("leaguePoints", 0),
                        "wins": e.get("wins", 0),
                        "losses": e.get("losses", 0),
                    }
                    if e.get("queueType") == "RANKED_SOLO_5x5":
                        solo = summary
                    elif e.get("queueType") == "RANKED_FLEX_SR":
                        flex = summary
        except RuntimeError:
            pass

        # 4. Champion mastery top 3
        top_champs: List[Dict[str, Any]] = []
        try:
            masteries = await _riot_get(
                client,
                f"https://{phost}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=3",
            )
            if isinstance(masteries, list):
                for m in masteries:
                    cid = m.get("championId")
                    top_champs.append({
                        "champion_id": cid,
                        "champion_name": champ_map.get(cid, f"Champion {cid}"),
                        "level": m.get("championLevel", 0),
                        "points": m.get("championPoints", 0),
                    })
        except RuntimeError:
            pass

    return {
        "riot_id": canonical_riot_id,
        "platform": platform,
        "region": PLATFORM_TO_REGION.get(platform, ""),
        "puuid": puuid,
        "summoner_id": summoner_id,
        "summoner_level": summoner_level,
        "solo_rank": solo,
        "flex_rank": flex,
        "top_champions": top_champs,
    }

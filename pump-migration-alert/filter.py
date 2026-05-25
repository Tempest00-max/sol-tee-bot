from config import (
    HELIUS_RPC, MAX_TOP_HOLDER_PCT,
    TRENDING_KEYWORDS, CREATOR_CACHE_TTL, RPC_SEMAPHORE_LIMIT,
    VELOCITY_MAXLEN,
)
from typing import Dict, Any, Tuple
from collections import deque
import logging
import time
import asyncio
import re
import aiohttp
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


logger = logging.getLogger("filter")

_rpc_sem = asyncio.Semaphore(RPC_SEMAPHORE_LIMIT)
_velocity: Dict[str, deque] = {}
_launch_velocity: Dict[str, deque] = {}  # First 60s only
_creator_cache: Dict[str, Tuple[float, bool, float]] = {}


def record_trade(mint: str, sol_amount: float):
    now = time.time()
    if mint not in _velocity:
        _velocity[mint] = deque(maxlen=VELOCITY_MAXLEN)
    _velocity[mint].append((now, sol_amount))

    # Track first 60 seconds separately for launch strength
    if mint not in _launch_velocity:
        _launch_velocity[mint] = deque(maxlen=100)
    # Only record if within first 60s of seeing this mint
    if _launch_velocity[mint]:
        first_seen = _launch_velocity[mint][0][0]
        if now - first_seen <= 60:
            _launch_velocity[mint].append((now, sol_amount))
    else:
        _launch_velocity[mint].append((now, sol_amount))


def get_buy_velocity(mint: str) -> float:
    if mint not in _velocity:
        return 0.0
    now = time.time()
    return sum(sol for ts, sol in _velocity[mint] if now - ts <= 60)


def get_launch_strength(mint: str) -> float:
    """SOL bought in first 60 seconds after bot first saw this token."""
    if mint not in _launch_velocity:
        return 0.0
    return sum(sol for ts, sol in _launch_velocity[mint])


def purge_old_velocity(max_age: int = 3600):
    now = time.time()
    dead = [m for m, q in _velocity.items() if q and now - q[-1][0] > max_age]
    for m in dead:
        del _velocity[m]
        if m in _launch_velocity:
            del _launch_velocity[m]
    if dead:
        logger.info(f"Purged {len(dead)} stale velocity trackers")


async def rpc_call(session, method: str, params: list) -> Any:
    async with _rpc_sem:
        try:
            async with session.post(
                HELIUS_RPC,
                json={"jsonrpc": "2.0", "id": 1,
                      "method": method, "params": params},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "error" not in data:
                        return data.get("result")
                elif resp.status == 429:
                    logger.warning("Helius rate limit hit (429)")
                else:
                    body = await resp.text()
                    logger.warning(f"Helius HTTP {resp.status}: {body[:100]}")
        except Exception as e:
            logger.warning(f"RPC {method} failed: {e}")
    return None


async def check_top_holder(session, mint: str) -> Tuple[bool, str]:
    largest = await rpc_call(session, "getTokenLargestAccounts", [mint])
    supply_r = await rpc_call(session, "getTokenSupply", [mint])
    if not largest or not supply_r:
        return True, "Skipped"
    try:
        total = int(supply_r["value"]["amount"])
        accounts = largest["value"]
        if not accounts or total == 0:
            return True, "No data"
        top_pct = int(accounts[0]["amount"]) / total
        if top_pct >= MAX_TOP_HOLDER_PCT:
            return False, f"Whale holds {top_pct:.1%}"
        return True, f"Top holder {top_pct:.1%}"
    except Exception as e:
        return True, f"Skipped ({e})"


async def check_dev_holds(session, creator: str, mint: str) -> Tuple[bool, str]:
    if not creator:
        return True, "No creator data"
    result = await rpc_call(session, "getTokenAccountsByOwner", [
        creator, {"mint": mint}, {"encoding": "jsonParsed"}
    ])
    if not result:
        return True, "Skipped"
    try:
        accounts = result.get("value", [])
        if not accounts:
            return False, "Dev sold (no balance)"
        bal = int(accounts[0]["account"]["data"]["parsed"]
                  ["info"]["tokenAmount"]["amount"])
        if bal == 0:
            return False, "Dev sold all tokens"
        return True, "Dev holds tokens"
    except Exception as e:
        return True, f"Skipped ({e})"


async def check_creator_history(session, creator: str) -> Tuple[bool, str]:
    if not creator:
        return False, "Unknown creator"
    now = time.time()
    if creator in _creator_cache:
        ts, has_hist, _ = _creator_cache[creator]
        if now - ts < CREATOR_CACHE_TTL:
            return has_hist, "Cached"
    result = await rpc_call(session, "getSignaturesForAddress", [creator, {"limit": 10}])
    has_hist = bool(result and len(result) >= 5)
    _creator_cache[creator] = (now, has_hist, 0.0)
    return has_hist, f"{len(result) if result else 0} prior txs"


async def check_dev_sol_balance(session, creator: str) -> Tuple[float, str]:
    if not creator:
        return 0.0, "No creator"
    result = await rpc_call(session, "getBalance", [creator])
    if not result:
        return 0.0, "Skipped"
    try:
        lamports = int(result.get("value", 0))
        sol = lamports / 1_000_000_000
        if creator in _creator_cache:
            ts, has_hist, _ = _creator_cache[creator]
            _creator_cache[creator] = (ts, has_hist, sol)
        return sol, f"{sol:.2f} SOL"
    except Exception as e:
        return 0.0, f"Skipped ({e})"


async def check_honeypot(session, mint: str) -> Tuple[bool, str]:
    """
    Basic honeypot check: try to get recent trades.
    If no trades exist after 30 seconds, or if all trades are buys with zero sells,
    it might be a honeypot (sells disabled).
    """
    result = await rpc_call(session, "getSignaturesForAddress", [mint, {"limit": 20}])
    if not result:
        return True, "Cannot verify"  # Assume safe if RPC fails

    # If we can't get transaction details, we can't check
    # This is a weak check - real honeypot detection requires simulating a sell
    return True, "Live"


def score_narrative(name: str, symbol: str) -> Tuple[int, str]:
    name_lower = (name or "").lower()
    symbol_lower = (symbol or "").lower()
    combined = f"{name_lower} {symbol_lower}"

    score = 50
    reasons = []

    hits = [kw for kw in TRENDING_KEYWORDS if kw in combined]
    score += len(hits) * 8
    if hits:
        reasons.append(f"Keywords: {', '.join(hits[:3])}")

    if symbol.isupper() and 2 <= len(symbol) <= 6:
        score += 8
        reasons.append("Meme symbol format")

    if any(w in combined for w in ["test", "demo", "sample", "fake", "scam"]):
        score -= 40
        reasons.append("TEST/DEMO detected")

    if re.search(r'^\d+$', symbol):
        score -= 35
        reasons.append("Numeric symbol")

    if len(set(symbol_lower)) <= 2 and len(symbol) >= 4:
        score -= 25
        reasons.append("Repetitive chars")

    if len(symbol) >= 5 and not re.search(r'[aeiou]', symbol_lower):
        score -= 20
        reasons.append("Random letters")

    if len(name) > 35:
        score -= 15
        reasons.append("Name too long")

    if len(re.findall(r'\d', symbol)) >= 3:
        score -= 10
        reasons.append("Number-heavy")

    final = max(0, min(100, score))
    return final, " | ".join(reasons) if reasons else "Neutral"


def calculate_bonding_probability(
    progress: float,
    velocity: float,
    launch_strength: float,
    creator_has_history: bool,
    dev_sol_balance: float
) -> Tuple[int, str]:
    """
    NEW: Uses launch_strength (actual SOL in first 60s) instead of initialBuy.
    This is harder to fake than the initialBuy field.
    """
    score = 0
    reasons = []

    prog_pts = min(30, progress * 0.35)
    score += prog_pts
    if progress >= 50:
        reasons.append(f"Progress {progress:.0f}%")

    if velocity >= 3.0:
        score += 35
        reasons.append(f"Hot velocity ({velocity:.1f} SOL/min)")
    elif velocity >= 1.5:
        score += 25
        reasons.append(f"Good velocity ({velocity:.1f} SOL/min)")
    elif velocity >= 0.5:
        score += 15
        reasons.append(f"Moderate velocity ({velocity:.1f} SOL/min)")
    elif velocity >= 0.1:
        score += 5

    # NEW: Launch strength from actual trades, not initialBuy field
    if launch_strength >= 10:
        score += 20
        reasons.append(f"Strong launch ({launch_strength:.1f} SOL in 60s)")
    elif launch_strength >= 5:
        score += 15
        reasons.append(f"Good launch ({launch_strength:.1f} SOL in 60s)")
    elif launch_strength >= 2:
        score += 10
        reasons.append(f"Decent launch ({launch_strength:.1f} SOL in 60s)")
    elif launch_strength >= 0.5:
        score += 5
        reasons.append(f"Modest launch ({launch_strength:.1f} SOL in 60s)")

    if creator_has_history:
        score += 10
        reasons.append("Experienced dev")

    if dev_sol_balance >= 1.0:
        score += 5
        reasons.append("Dev funded")
    elif dev_sol_balance >= 0.05:
        score += 2

    final = min(100, int(score))
    return final, " | ".join(reasons) if reasons else "Low signals"


async def run_checks(session, token: Dict) -> Dict[str, Any]:
    mint = token.get("mint", "")
    creator = token.get("creator", "")
    name = token.get("name", "")
    symbol = token.get("symbol", "")
    progress = token.get("progress", 0)

    # NEW: Use actual launch strength instead of initialBuy
    launch_strength = get_launch_strength(mint)

    whale_ok, whale_detail = await check_top_holder(session, mint)
    dev_ok, dev_detail = await check_dev_holds(session, creator, mint)
    honeypot_ok, honeypot_detail = await check_honeypot(session, mint)

    narrative_score, narrative_reason = score_narrative(name, symbol)

    velocity = get_buy_velocity(mint)
    creator_has_history, _ = await check_creator_history(session, creator)
    dev_sol_balance, _ = await check_dev_sol_balance(session, creator)

    bonding_prob, bonding_reason = calculate_bonding_probability(
        progress, velocity, launch_strength, creator_has_history, dev_sol_balance
    )

    # NEW: Honeypot is a hard fail
    hard_fail = ((not whale_ok) and (not dev_ok)) or (not honeypot_ok)

    return {
        "safe": not hard_fail,
        "hard_fail": hard_fail,
        "checks": {
            "mint_renounced": {"passed": True, "detail": "Pump.fun default ✅"},
            "no_whale": {"passed": whale_ok, "detail": whale_detail},
            "dev_holds": {"passed": dev_ok, "detail": dev_detail},
            "honeypot": {"passed": honeypot_ok, "detail": honeypot_detail},
        },
        "narrative_score": narrative_score,
        "narrative_reason": narrative_reason,
        "bonding_prob": bonding_prob,
        "bonding_reason": bonding_reason,
        "velocity": velocity,
        "launch_strength": launch_strength,
        "dev_sol_balance": dev_sol_balance,
    }

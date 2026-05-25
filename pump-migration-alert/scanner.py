import stats
from price_feed import refresh_sol_price, price_loop
from alert import (
    send_telegram, build_tier_alert,
    build_milestone_alert, build_startup, can_alert,
)
from filter import run_checks, record_trade, purge_old_velocity, get_buy_velocity
from bonding_curve import extract_info, get_tier
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, HELIUS_API_KEY,
    TIER_EARLY, TIER_MOMENTUM, TIER_IMMINENT,
    MILESTONE_XS,
    MIN_MARKET_CAP_USD, MIN_PROGRESS_PCT, MIN_VELOCITY_SOL,
    MIN_NARRATIVE_SCORE, MIN_BONDING_PROB,
    CACHE_PURGE_INTERVAL, TOKEN_MAX_AGE, ALERT_COOLDOWN_SECONDS,
    PRICE_REFRESH_INTERVAL,
)
from typing import Dict, Optional
from datetime import datetime, timezone
import signal
import logging
import json
import aiosqlite
import websockets
import aiohttp
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-10s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.FileHandler("data/teebot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("scanner")

cache: Dict[str, dict] = {}
_shutdown = asyncio.Event()
_last_seen_update: Dict[str, float] = {}


async def init_db():
    os.makedirs("data", exist_ok=True)
    db = await aiosqlite.connect("data/teebot.db")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            mint            TEXT PRIMARY KEY,
            name            TEXT,
            symbol          TEXT,
            first_mc_sol    REAL,
            first_progress  REAL,
            first_tier      TEXT,
            first_alerted   TEXT,
            tiers_sent      TEXT DEFAULT '[]',
            milestones_sent TEXT DEFAULT '[]',
            narrative_score INTEGER,
            bonding_prob    INTEGER,
            max_multiplier  REAL DEFAULT 0,
            outcome         TEXT DEFAULT 'pending',
            last_seen       REAL DEFAULT 0,
            alert_count     INTEGER DEFAULT 0
        )
    """)
    try:
        await db.execute("ALTER TABLE tokens ADD COLUMN alert_count INTEGER DEFAULT 0")
    except Exception:
        pass
    await db.commit()
    return db


async def db_get(db: aiosqlite.Connection, mint: str) -> Optional[dict]:
    async with db.execute("SELECT * FROM tokens WHERE mint=?", (mint,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    cols = ["mint", "name", "symbol", "first_mc_sol", "first_progress",
            "first_tier", "first_alerted", "tiers_sent", "milestones_sent",
            "narrative_score", "bonding_prob", "max_multiplier", "outcome", "last_seen", "alert_count"]
    d = dict(zip(cols, row))
    d["tiers_sent"] = set(json.loads(d["tiers_sent"]))
    d["milestones_sent"] = set(json.loads(d["milestones_sent"]))
    return d


async def db_insert(db: aiosqlite.Connection, token: dict, tier: str, mc_sol: float, progress: float,
                    narrative_score: int, bonding_prob: int):
    now_iso = datetime.now(timezone.utc).isoformat()
    now_ts = datetime.now(timezone.utc).timestamp()
    await db.execute("""
        INSERT OR IGNORE INTO tokens
            (mint, name, symbol, first_mc_sol, first_progress,
             first_tier, first_alerted, tiers_sent, milestones_sent,
             narrative_score, bonding_prob, last_seen, alert_count)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        token["mint"], token["name"], token["symbol"],
        mc_sol, progress, tier, now_iso,
        json.dumps([tier]), json.dumps([]),
        narrative_score, bonding_prob, now_ts, 1
    ))
    await db.commit()
    await stats.record_call(db)


async def db_add_tier(db: aiosqlite.Connection, mint: str, tier: str):
    row = await db_get(db, mint)
    if not row:
        return
    tiers = list(row["tiers_sent"]) + [tier]
    await db.execute("UPDATE tokens SET tiers_sent=?, alert_count = alert_count + 1 WHERE mint=?",
                     (json.dumps(list(set(tiers))), mint))
    await db.commit()


async def db_update_milestones(db: aiosqlite.Connection, mint: str, milestones_set: set):
    await db.execute(
        "UPDATE tokens SET milestones_sent=? WHERE mint=?",
        (json.dumps(list(milestones_set)), mint)
    )
    await db.commit()


async def db_update_last_seen(db: aiosqlite.Connection, mint: str):
    now = datetime.now(timezone.utc).timestamp()
    last = _last_seen_update.get(mint, 0)
    if now - last < 300:
        return
    _last_seen_update[mint] = now
    await db.execute("UPDATE tokens SET last_seen=? WHERE mint=?", (now, mint))
    await db.commit()


async def load_cache(db: aiosqlite.Connection):
    global cache
    async with db.execute(
        "SELECT mint, first_mc_sol, tiers_sent, milestones_sent FROM tokens"
    ) as cursor:
        rows = await cursor.fetchall()
    for mint, first_mc_sol, tiers_json, ms_json in rows:
        cache[mint] = {
            "first_mc_sol":    first_mc_sol,
            "tiers_sent":      set(json.loads(tiers_json)),
            "milestones_sent": set(json.loads(ms_json)),
        }
    logger.info(f"Loaded {len(cache)} previously alerted tokens from database")


def validate_config() -> bool:
    missing = []
    if not HELIUS_API_KEY:
        missing.append("HELIUS_API_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        logger.error("config.py is incomplete. Fill in: " + ", ".join(missing))
        return False
    return True


async def cache_purge_loop():
    while not _shutdown.is_set():
        await _shutdown.wait(CACHE_PURGE_INTERVAL)
        if _shutdown.is_set():
            break
        now = datetime.now(timezone.utc).timestamp()
        dead = [m for m, st in cache.items() if now -
                st.get("last_seen", now) > TOKEN_MAX_AGE]
        for m in dead:
            del cache[m]
        if dead:
            logger.info(f"Purged {len(dead)} stale tokens from cache")
        purge_old_velocity()


async def handle_event(event: dict, session: aiohttp.ClientSession, db: aiosqlite.Connection):
    tx_type = event.get("txType", "")
    has_vsol = "vSolInBondingCurve" in event

    # Record ALL trades for velocity tracking
    if tx_type in ("swap", "buy", "sell") or "solAmount" in event:
        mint = event.get("mint", "")
        sol_amt = float(event.get("solAmount")
                        or event.get("tokenAmount") or 0)
        if mint and sol_amt > 0:
            record_trade(mint, sol_amt)

    if not has_vsol and tx_type != "create":
        return
    if tx_type == "complete":
        return

    token = extract_info(event)
    mint = token["mint"]
    progress = token["progress"]
    mc_sol = token["mc_sol"]
    mc_usd = token["mc_usd"]

    if not mint:
        return

    # ═══════════════════════════════════════════════════════════
    #  STRICT ENTRY THRESHOLDS (v6 — NO LAUNCH ALERTS)
    # ═══════════════════════════════════════════════════════════

    # Skip if below minimum market cap
    if mc_usd < MIN_MARKET_CAP_USD:
        return  # Too small, likely rug or dead

    # Skip if below minimum progress
    if progress < MIN_PROGRESS_PCT:
        return  # Too early, no proven momentum

    # Skip if velocity too low
    velocity = get_buy_velocity(mint)
    if velocity < MIN_VELOCITY_SOL:
        return  # No real buying pressure

    # ── ALREADY TRACKING THIS TOKEN ──────────────────────────
    if mint in cache:
        state = cache[mint]
        first_mc = state["first_mc_sol"]

        await db_update_last_seen(db, mint)

        # Milestone check
        if first_mc and first_mc > 0 and mc_sol > 0:
            mult = mc_sol / first_mc
            new_hits = [x for x in MILESTONE_XS if mult >=
                        x and x not in state["milestones_sent"]]
            if new_hits:
                symbol = token["symbol"]
                logger.info(f"MILESTONE: {symbol} hit {new_hits}")
                stats_data = await stats.get_stats(db)
                stats_str = stats.format_stats(stats_data)
                for target_x in new_hits:
                    msg = build_milestone_alert(
                        token, target_x, first_mc, stats_str=stats_str)
                    await send_telegram(session, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)
                    state["milestones_sent"].add(target_x)
                    await stats.record_hit(db, mult, mint, token.get("name", ""))
                await db_update_milestones(db, mint, state["milestones_sent"])
                await db.execute(
                    "UPDATE tokens SET max_multiplier = MAX(max_multiplier, ?) WHERE mint = ?",
                    (mult, mint)
                )
                await db.commit()

        # Tier upgrade check
        current_tier = get_tier(progress)
        if current_tier and current_tier not in state["tiers_sent"]:
            if not can_alert(mint, ALERT_COOLDOWN_SECONDS):
                return
            symbol = token["symbol"]
            logger.info(
                f"TIER UPGRADE: {symbol} → {current_tier} ({progress:.0f}%)")
            safety = await run_checks(session, token)
            msg = build_tier_alert(
                token, safety, current_tier, first_mc_sol=first_mc)
            sent = await send_telegram(session, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)
            if sent:
                state["tiers_sent"].add(current_tier)
                await db_add_tier(db, mint, current_tier)
        return

    # ── NEW TOKEN MEETS THRESHOLDS ───────────────────────────
    # No more launch alerts. Only alert if token has proven momentum.
    tier = get_tier(progress)
    if tier is None:
        return  # Not in any alert zone yet

    name = token["name"]
    symbol = token["symbol"]
    logger.info(f"NEW SIGNAL: {name} (${symbol}) — {tier} ({progress:.0f}%) | "
                f"MC: ${mc_usd:,.0f} | Velocity: {velocity:.2f} SOL/min")

    safety = await run_checks(session, token)

    if safety.get("narrative_score", 0) < MIN_NARRATIVE_SCORE:
        logger.info(
            f"  ✗ Narrative too weak ({safety['narrative_score']}/100)")
        return
    if safety.get("bonding_prob", 0) < MIN_BONDING_PROB:
        logger.info(f"  ✗ Bonding unlikely ({safety['bonding_prob']}/100)")
        return
    if safety.get("hard_fail"):
        logger.info(f"  ✗ Hard fail — skipping")
        return

    if not can_alert(mint, ALERT_COOLDOWN_SECONDS):
        return

    msg = build_tier_alert(token, safety, tier)
    sent = await send_telegram(session, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)

    if sent:
        cache[mint] = {
            "first_mc_sol": mc_sol,
            "tiers_sent": {tier},
            "milestones_sent": set(),
        }
        await db_insert(db, token, tier, mc_sol, progress,
                        safety["narrative_score"], safety["bonding_prob"])
        logger.info(f"  ✅ FIRST ALERT sent: {mint[:20]}... "
                    f"(MC: ${mc_usd:,.0f}, Narrative: {safety['narrative_score']}, "
                    f"Bonding: {safety['bonding_prob']}%)")
    else:
        logger.warning(f"  ✗ Telegram failed")


async def main():
    logger.info("=" * 58)
    logger.info("TEE-BOT v6 — Momentum-Only Edition")
    logger.info("=" * 58)
    logger.info(f"  👀 Early    → {TIER_EARLY:.0f}%+ bonded")
    logger.info(f"  🔥 Momentum → {TIER_MOMENTUM:.0f}%+ bonded")
    logger.info(f"  🚀 Imminent → {TIER_IMMINENT:.0f}%+ bonded")
    logger.info(f"  💰 Min MC   → ${MIN_MARKET_CAP_USD:,.0f}")
    logger.info(f"  📈 Min Vel  → {MIN_VELOCITY_SOL} SOL/min")
    logger.info(f"  🧠 Narrative min → {MIN_NARRATIVE_SCORE}/100")
    logger.info(f"  📊 Bonding prob min → {MIN_BONDING_PROB}/100")
    logger.info("=" * 58)

    if not validate_config():
        return

    db = await init_db()
    await stats.init_stats_db(db)
    await load_cache(db)

    async with aiohttp.ClientSession() as session:
        await refresh_sol_price(session)

        s = await stats.get_stats(db)
        startup_msg = build_startup(stats_str=stats.format_stats(s))
        await send_telegram(session, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, startup_msg)
        logger.info("Startup message sent to Telegram")

        asyncio.create_task(price_loop(session, PRICE_REFRESH_INTERVAL))
        asyncio.create_task(cache_purge_loop())

        while not _shutdown.is_set():
            try:
                now = datetime.now().strftime("%H:%M:%S")
                logger.info(f"[{now}] Connecting to pumpportal.fun...")

                async with websockets.connect(
                    PUMPPORTAL_WS,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    await ws.send(json.dumps({"method": "subscribeNewToken"}))
                    await ws.send(json.dumps({"method": "subscribeTokenTrade", "keys": []}))

                    logger.info(
                        "WebSocket live. Monitoring all launches + all trades.")

                    async for raw_message in ws:
                        if _shutdown.is_set():
                            break
                        try:
                            event = json.loads(raw_message)
                            await handle_event(event, session, db)
                        except json.JSONDecodeError:
                            pass
                        except Exception as e:
                            logger.exception(f"Event error: {e}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket closed. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.exception(f"WS error: {e}")
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

        logger.info("Shutting down...")
        try:
            await send_telegram(session, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, "🔴 TEE-BOT v6 stopped.")
        except Exception:
            pass
        await db.close()


def _signal_handler(sig_num):
    sig_name = signal.Signals(sig_num).name
    logger.info(f"Received signal {sig_name}")
    _shutdown.set()


if __name__ == "__main__":
    import signal
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: _signal_handler(s))
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()

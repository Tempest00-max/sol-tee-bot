from config import TIER_EARLY, TIER_MOMENTUM, TIER_IMMINENT
from bonding_curve import format_bar, get_tier_meta
from typing import Dict, Optional
from datetime import datetime
import logging
import time
import html
import aiohttp
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


logger = logging.getLogger("alert")
_last_alert_ts: Dict[str, float] = {}


def _e(text) -> str:
    return html.escape(str(text) if text else "")


def _x_display(multiplier: float) -> str:
    if multiplier >= 50:
        return f"💎 <b>{multiplier:.0f}x FROM OUR CALL</b> 💎"
    elif multiplier >= 10:
        return f"🤑 <b>{multiplier:.1f}x FROM OUR CALL</b>"
    elif multiplier >= 5:
        return f"🔥 <b>{multiplier:.1f}x FROM OUR CALL</b>"
    elif multiplier >= 2:
        return f"📈 <b>{multiplier:.1f}x FROM OUR CALL</b>"
    else:
        return f"➡️ {multiplier:.1f}x from our call"


def _time_estimate(vsol: float, progress: float) -> str:
    sol_left = max(0, 85.0 - vsol)
    if progress >= 95:
        return "⏱ Migrating now"
    elif progress >= 80:
        return f"⏱ ~{max(1, int(sol_left * 0.8))} min to graduation"
    elif progress >= 45:
        return f"⏱ ~{max(3, int(sol_left * 1.5))} min to graduation"
    else:
        return f"⏱ ~{max(10, int(sol_left * 2.5))} min to graduation"


def _score_bar(score: int, width: int = 10) -> str:
    filled = int((score / 100) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {score}"


def can_alert(mint: str, cooldown: int = 300) -> bool:
    now = time.time()
    last = _last_alert_ts.get(mint, 0)
    if now - last < cooldown:
        return False
    _last_alert_ts[mint] = now
    return True


def build_tier_alert(token: Dict, safety: Dict, tier: str, first_mc_sol: Optional[float] = None) -> str:
    meta = get_tier_meta(tier)
    name = _e(token["name"])
    symbol = _e(token["symbol"])
    mint = _e(token["mint"])

    progress = token["progress"]
    vsol = token["vsol"]
    mc_sol = token["mc_sol"]
    mc_usd = token["mc_usd"]
    bar = format_bar(progress)

    checks = safety.get("checks", {})
    w_ok = checks.get("no_whale", {}).get("passed", True)
    d_ok = checks.get("dev_holds", {}).get("passed", True)
    h_ok = checks.get("honeypot", {}).get("passed", True)
    w_icon = "✅" if w_ok else "⚠️"
    d_icon = "✅" if d_ok else "⚠️"
    h_icon = "✅" if h_ok else "🚫"
    w_det = _e(checks.get("no_whale", {}).get("detail", ""))
    d_det = _e(checks.get("dev_holds", {}).get("detail", ""))
    h_det = _e(checks.get("honeypot", {}).get("detail", ""))

    nar_score = safety.get("narrative_score", 0)
    bond_prob = safety.get("bonding_prob", 0)
    nar_reason = _e(safety.get("narrative_reason", ""))
    bond_reason = _e(safety.get("bonding_reason", ""))
    launch_str = safety.get("launch_strength", 0)

    x_line = ""
    if first_mc_sol and first_mc_sol > 0 and mc_sol > 0:
        mult = mc_sol / first_mc_sol
        x_line = f"\n{_x_display(mult)}\n"

    time_str = _time_estimate(vsol, progress)
    first_line = f"{meta['emoji']} <b>{meta['label']}</b>"

    launch_line = f"Launch strength: <b>{launch_str:.2f} SOL</b> (first 60s)\n" if launch_str > 0 else ""

    return f"""{first_line}{x_line}
<b>{name}</b> (${symbol})

{bar}
vSol: <b>{vsol:.1f} / 85 SOL</b>
Market cap: <b>{mc_sol:.1f} SOL</b> ≈ <b>${mc_usd:,.0f}</b>
{time_str}

{launch_line}<b>🧠 Narrative:</b> {_score_bar(nar_score)} — <i>{nar_reason}</i>
<b>📊 Bonding Probability:</b> {_score_bar(bond_prob)} — <i>{bond_reason}</i>

Safety:
• Mint renounced: ✅ (Pump.fun default)
• Whale check: {w_icon}  <i>{w_det}</i>
• Dev holds: {d_icon}  <i>{d_det}</i>
• Honeypot: {h_icon}  <i>{h_det}</i>

<i>{meta['action']}</i>
<i>{meta['risk']}</i>

<code>{mint}</code>
<a href="https://pump.fun/{mint}">pump.fun</a> · <a href="https://birdeye.so/token/{mint}">Birdeye</a> · <a href="https://solscan.io/token/{mint}">Solscan</a>

<i>DYOR — Not financial advice — TEE-BOT</i>"""


def build_milestone_alert(token: Dict, multiplier: float, first_mc_sol: float, stats_str: Optional[str] = None) -> str:
    name = _e(token["name"])
    symbol = _e(token["symbol"])
    mint = _e(token["mint"])
    mc_sol = token["mc_sol"]
    mc_usd = token["mc_usd"]
    first_usd = first_mc_sol * (mc_usd / mc_sol if mc_sol else 0)
    bar = format_bar(token["progress"])
    progress = token["progress"]

    if multiplier >= 50:
        header = f"💎 <b>MILESTONE: {multiplier:.0f}x</b> 💎"
    elif multiplier >= 10:
        header = f"🤑 <b>MILESTONE: {multiplier:.0f}x REACHED</b>"
    elif multiplier >= 5:
        header = f"💰 <b>MILESTONE: {multiplier:.0f}x REACHED</b>"
    else:
        header = f"📈 <b>MILESTONE: {multiplier:.0f}x REACHED</b>"

    still_on_curve = "Still on bonding curve — migration ahead" if progress < 100 else "Now on Raydium"
    track_record = f"\n\n{stats_str}" if stats_str else ""

    return f"""{header}

<b>{name}</b> (${symbol})

First called at: <b>${first_usd:,.0f}</b>
Now trading at:  <b>${mc_usd:,.0f}</b>
Return: <b>{multiplier:.1f}x 🔥</b>

{bar}
{still_on_curve}

<code>{mint}</code>
<a href="https://pump.fun/{mint}">pump.fun</a> · <a href="https://birdeye.so/token/{mint}">Birdeye</a>

<i>TEE-BOT first called this at ${first_usd:,.0f}</i>{track_record}"""


def build_startup(stats_str: Optional[str] = None) -> str:
    base = (
        f"🤖 <b>TEE-BOT v6 — Momentum Filter Live</b>\n\n"
        f"✅ Only tokens with proven momentum are alerted:\n"
        f"💰 Minimum market cap: <b>$10,000</b>\n"
        f"📈 Minimum progress: <b>15%</b> bonded\n"
        f"⚡ Minimum velocity: <b>0.5 SOL/min</b>\n\n"
        f"Alert tiers:\n"
        f"👀 EARLY    — {TIER_EARLY:.0f}%+ bonded, first movers\n"
        f"🔥 MOMENTUM — {TIER_MOMENTUM:.0f}%+ bonded, confirmed buying\n"
        f"🚀 IMMINENT — {TIER_IMMINENT:.0f}%+ bonded, migration soon\n\n"
        f"🧠 Narrative filter: Only real themes pass.\n"
        f"📊 Bonding predictor: Estimates graduation odds.\n"
        f"📈 Live track record on every milestone.\n\n"
        f"🎯 Milestone alerts: 2x · 5x · 10x · 25x · 50x · 100x\n"
        f"Each later alert shows X from first call.\n\n"
        f"{_e(datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))}"
    )
    if stats_str:
        base += f"\n\n{stats_str}"
    return base


async def send_telegram(session: aiohttp.ClientSession, bot_token: str, chat_id: str, message: str) -> bool:
    if not bot_token or not chat_id:
        logger.warning(f"TG not configured. Preview: {message[:80]}...")
        return False
    try:
        async with session.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status == 200:
                return True
            body = await resp.text()
            logger.warning(f"TG HTTP {resp.status}: {body[:200]}")
            if resp.status == 429:
                logger.error("Telegram rate limit — backing off 2s")
                await asyncio.sleep(2)
            return False
    except Exception as e:
        logger.warning(f"TG send failed: {e}")
        return False

from price_feed import get_sol_price
from config import TIER_EARLY, TIER_MOMENTUM, TIER_IMMINENT
from typing import Dict, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


VIRT_SOL_START = 30.0
VIRT_SOL_MIGRATION = 85.0


def calculate_progress(vsol: float) -> float:
    if vsol is None or vsol <= VIRT_SOL_START:
        return 0.0
    return max(0.0, min(
        (vsol - VIRT_SOL_START) / (VIRT_SOL_MIGRATION - VIRT_SOL_START) * 100,
        100.0
    ))


def get_tier(progress: float) -> Optional[str]:
    if progress >= TIER_IMMINENT:
        return "imminent"
    if progress >= TIER_MOMENTUM:
        return "momentum"
    if progress >= TIER_EARLY:
        return "early"
    return None


TIER_META = {
    "launch": {
        "emoji": "🌱",
        "label": "FRESH LAUNCH",
        "action": "Just launched. Ground floor entry.",
        "risk":   "🔴 VERY HIGH RISK — most new tokens fail.",
    },
    "early": {
        "emoji": "👀",
        "label": "EARLY ENTRY",
        "action": "Early buyers accumulating. Room left.",
        "risk":   "🟠 HIGH RISK — early stage. Size small.",
    },
    "momentum": {
        "emoji": "🔥",
        "label": "MOMENTUM BUILDING",
        "action": "Sustained buying confirmed.",
        "risk":   "🟡 MEDIUM RISK — watch for reversal.",
    },
    "imminent": {
        "emoji": "🚀",
        "label": "MIGRATION IMMINENT",
        "action": "Final stage before Raydium. Minutes away.",
        "risk":   "🟢 LOWER RISK (migration likely) — manage exit.",
    },
}


def get_tier_meta(tier: str) -> dict:
    return TIER_META.get(tier, {"emoji": "📡", "label": tier.upper(), "action": "", "risk": ""})


def format_bar(progress: float, width: int = 10) -> str:
    filled = int((min(progress, 100) / 100) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {progress:.0f}%"


def extract_info(event: Dict) -> Dict:
    vsol_raw = event.get("vSolInBondingCurve")
    vsol = float(vsol_raw) if vsol_raw is not None else VIRT_SOL_START

    mc_sol_raw = event.get("marketCapSol")
    mc_sol = float(mc_sol_raw) if mc_sol_raw is not None else 0.0

    # REMOVED: initialBuy is unreliable. Launch strength is computed from actual trades.
    return {
        "mint":        event.get("mint", ""),
        "name":        event.get("name") or "Unknown",
        "symbol":      event.get("symbol") or "???",
        "creator":     event.get("traderPublicKey") or event.get("creator", ""),
        "vsol":        vsol,
        "vtokens":     event.get("vTokensInBondingCurve") or 0,
        "mc_sol":      mc_sol,
        "mc_usd":      mc_sol * get_sol_price(),
        "progress":    calculate_progress(vsol),
        "is_complete": event.get("txType") == "complete" or bool(event.get("complete")),
        "initial_buy": 0.0,  # Now computed from actual trades in filter.py
        "tx_type":     event.get("txType", ""),
    }

"""
TEE-BOT v6 — config.py template
Copy to config.py and fill in your real values (never commit config.py)
"""

# ── Credentials ───────────────────────────────────────────────
HELIUS_API_KEY = "YOUR_HELIUS_API_KEY_HERE"
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID_HERE"

# ── RPC ─────────────────────────────────────────────────────
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# ── Tiers ───────────────────────────────────────────────────
TIER_EARLY = 12.0
TIER_MOMENTUM = 40.0
TIER_IMMINENT = 78.0

# ── MINIMUM THRESHOLDS ──────────────────────────────────────
MIN_MARKET_CAP_USD = 10000
MIN_PROGRESS_PCT = 15.0
MIN_VELOCITY_SOL = 0.5
MIN_LAUNCH_BUY_SOL = 0.5

# ── Milestones ──────────────────────────────────────────────
MILESTONE_XS = [2.0, 5.0, 10.0, 25.0, 50.0, 100.0]

# ── Safety ──────────────────────────────────────────────────
MAX_TOP_HOLDER_PCT = 0.20

# ── Narrative & Bonding ─────────────────────────────────────
MIN_NARRATIVE_SCORE = 35
MIN_BONDING_PROB = 50

TRENDING_KEYWORDS = [
    "ai", "gpt", "bot", "agent", "neural", "deep", "intelligence",
    "meme", "pepe", "doge", "shib", "wojak", "chad", "bonk", "mog",
    "trump", "maga", "america", "usa", "president", "biden", "elon",
    "musk", "tesla", "space", "mars", "rocket", "moon", "lambo",
    "cat", "kitty", "dog", "puppy", "frog", "bird", "animal",
    "sol", "solana", "pump", "fun", "based", "hodl", "diamond",
    "hands", "ape", "degen", "wagmi", "gm", "gn", "ser", "anon",
    "crypto", "coin", "token", "gold", "btc", "bitcoin", "eth",
    "meta", "verse", "web3", "nft", "dao", "game", "gaming",
    "viral", "trend", "legend", "god", "king", "queen", "boss"
]

# ── Infrastructure ──────────────────────────────────────────
RPC_SEMAPHORE_LIMIT = 5
CREATOR_CACHE_TTL = 600
ALERT_COOLDOWN_SECONDS = 300
VELOCITY_MAXLEN = 50
CACHE_PURGE_INTERVAL = 3600
TOKEN_MAX_AGE = 86400
PRICE_REFRESH_INTERVAL = 300

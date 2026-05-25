# TEE-BOT — Pump.fun Migration Alert System

Real-time monitoring of Pump.fun bonding curves. Sends Telegram alerts when tokens hit 85% bonded — minutes before Raydium migration.

## What it does

- Scans Pump.fun every 30 seconds for tokens approaching graduation
- Checks contract renouncement, whale concentration, and dev wallet history
- Sends instant Telegram alert with safety data + direct links
- Deduplicates via SQLite — no repeat alerts

## Setup (15 minutes)

### 1. Get a free Helius API key
Go to [helius.dev](https://helius.dev) → Sign up → Copy your API key

### 2. Create a Telegram bot
- Message [@BotFather](https://t.me/BotFather) on Telegram
- Send `/newbot` → follow prompts → copy the token
- Message [@userinfobot](https://t.me/userinfobot) → copy your ID

### 3. Install and run

```bash
# On Termux (Android) or any Python 3.8+ environment
pip install aiohttp

# Edit config.py with your keys
nano config.py

# Run
python scanner.py
```

### Keep running on Android (Termux)

```bash
termux-wake-lock
nohup python scanner.py > scanner.log 2>&1 &
```

### Deploy free on Render.com

1. Push this folder to GitHub
2. Connect at [render.com](https://render.com)
3. New Web Service → connect repo → Start command: `python scanner.py`

## File structure

```
pump-migration-alert/
├── scanner.py          Main loop — run this
├── bonding_curve.py    Pump.fun API + migration math
├── filter.py           On-chain safety checks
├── alert.py            Telegram message builder
├── config.py           Your API keys and thresholds
├── requirements.txt    One dependency: aiohttp
└── data/
    └── seen_tokens.db  Auto-created SQLite database
```

## Tech stack

- Python 3.8+
- aiohttp (async HTTP)
- Helius RPC (free tier)
- Pump.fun public API
- SQLite (no server needed)
- Telegram Bot API

## Alert example

```
🟢 MIGRATION ALERT — entering zone

DOGE2 ($DOGE2)

Bonding progress:
[████████░░] 83%

Market cap:  $57,400
24h volume:  $312,000
Est. to graduation: ~8 min

Safety checks:
• Mint renounced:       ✅
• No whale concentration: ✅
• Dev wallet history:   ✅

Contract: AbCdEfGhIjKlMnOpQr...
pump.fun | Solscan | Birdeye
```

## Custom builds

I build custom versions with:
- Auto-buy on migration signal
- Smart wallet overlay (alerts when known profitable wallets buy)
- Discord / webhook alerts
- Multi-channel support
- Private hosted instances

DM on Twitter: [@joe_richma49107]

## License

MIT
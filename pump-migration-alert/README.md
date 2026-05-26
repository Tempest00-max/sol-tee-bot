# TEE-BOT — Pump.fun Migration Alert System

Real-time monitoring of Pump.fun bonding curves with async Python, 
SQLite persistence, and Telegram alerting.

## Architecture

- **scanner.py** — Async event loop scanning Pump.fun API every 30s
- **bonding_curve.py** — Bonding curve math and migration probability
- **filter.py** — On-chain safety validation (renouncement, whale checks)
- **alert.py** — Telegram message builder with deduplication
- **config.py** — Environment configuration (gitignored, see config.example.py)

## Tech Stack

- Python 3.11 + asyncio + aiohttp
- Helius RPC for Solana blockchain data
- SQLite for token deduplication
- Telegram Bot API for alerts

## Key Design Decisions

- **Async architecture** — Single event loop handles scanning, filtering, 
  and alerting without blocking
- **SQLite deduplication** — Prevents alert spam via persistent state
- **Modular safety checks** — Renouncement, whale concentration, and dev 
  wallet history evaluated independently
- **Configurable thresholds** — Market cap, velocity, and bonding progress 
  tunable per deployment

## Setup

```bash
pip install -r requirements.txt
cp config.example.py config.py
# Edit config.py with your API keys
python scanner.py

from typing import Dict
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def init_stats_db(db):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_stats (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            total_calls INTEGER DEFAULT 0,
            hits_2x  INTEGER DEFAULT 0,
            hits_5x  INTEGER DEFAULT 0,
            hits_10x INTEGER DEFAULT 0,
            hits_25x INTEGER DEFAULT 0,
            hits_50x INTEGER DEFAULT 0,
            hits_100x INTEGER DEFAULT 0,
            best_multiplier REAL DEFAULT 0.0,
            best_mint TEXT DEFAULT '',
            best_name TEXT DEFAULT ''
        )
    """)
    await db.execute("INSERT OR IGNORE INTO bot_stats (id) VALUES (1)")
    await db.commit()


async def record_call(db):
    await db.execute("UPDATE bot_stats SET total_calls = total_calls + 1 WHERE id = 1")
    await db.commit()


async def record_hit(db, multiplier: float, mint: str, name: str):
    col = None
    if multiplier >= 100:
        col = "hits_100x"
    elif multiplier >= 50:
        col = "hits_50x"
    elif multiplier >= 25:
        col = "hits_25x"
    elif multiplier >= 10:
        col = "hits_10x"
    elif multiplier >= 5:
        col = "hits_5x"
    elif multiplier >= 2:
        col = "hits_2x"

    if col:
        await db.execute(f"UPDATE bot_stats SET {col} = {col} + 1 WHERE id = 1")

    async with db.execute("SELECT best_multiplier FROM bot_stats WHERE id = 1") as cursor:
        row = await cursor.fetchone()

    current_best = row[0] if row else 0.0
    if multiplier > current_best:
        await db.execute(
            "UPDATE bot_stats SET best_multiplier = ?, best_mint = ?, best_name = ? WHERE id = 1",
            (multiplier, mint, name),
        )
    await db.commit()


async def get_stats(db) -> Dict:
    async with db.execute("SELECT * FROM bot_stats WHERE id = 1") as cursor:
        row = await cursor.fetchone()
    if not row:
        return {}
    keys = ["id", "total_calls", "hits_2x", "hits_5x", "hits_10x", "hits_25x",
            "hits_50x", "hits_100x", "best_multiplier", "best_mint", "best_name"]
    return dict(zip(keys, row))


def format_stats(stats: Dict) -> str:
    total = stats.get("total_calls", 0)
    if total == 0:
        return "📊 Track record: No calls yet."

    lines = ["📊 <b>BOT TRACK RECORD</b>", f"Total calls: <b>{total}</b>"]
    buckets = [
        ("2x+",  "hits_2x"),
        ("5x+",  "hits_5x"),
        ("10x+", "hits_10x"),
        ("25x+", "hits_25x"),
        ("50x+", "hits_50x"),
        ("100x+", "hits_100x"),
    ]
    for label, col in buckets:
        val = stats.get(col, 0)
        pct = (val / total * 100) if total else 0
        lines.append(f"• {label:<6} <b>{val}</b>  ({pct:.0f}%)")

    if stats.get("best_multiplier", 0) > 0:
        lines.append(
            f"\n🏆 Best call: <b>{stats['best_multiplier']:.1f}x</b> "
            f"({stats.get('best_name', '')})"
        )
    return "\n".join(lines)

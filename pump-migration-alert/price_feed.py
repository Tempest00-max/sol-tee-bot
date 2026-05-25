import logging
import aiohttp
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


logger = logging.getLogger("price")

BINANCE_SOL_USDT = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"
_sol_price = 165.0


async def refresh_sol_price(session: aiohttp.ClientSession) -> float:
    global _sol_price
    try:
        async with session.get(BINANCE_SOL_USDT, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                price = float(data.get("price", _sol_price))
                _sol_price = price
                logger.info(f"SOL price updated: ${price:.2f}")
                return price
    except Exception as e:
        logger.warning(f"Price fetch failed: {e}")
    return _sol_price


def get_sol_price() -> float:
    return _sol_price


async def price_loop(session: aiohttp.ClientSession, interval: int):
    while True:
        await refresh_sol_price(session)
        await asyncio.sleep(interval)

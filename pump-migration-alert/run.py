import scanner
import asyncio
import sys
import os

folder = os.path.dirname(os.path.abspath(__file__))
if folder not in sys.path:
    sys.path.insert(0, folder)


asyncio.run(scanner.main())

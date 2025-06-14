"""
Showcase: Extract a message addressed to my callsign (sync)
"""
import asyncio
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs
from ax253 import Frame

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    await aprs.connect()  # Synchronous connect for the dummy backend
    info = b":N0CALL-1 :test message{123"
    frame = Frame(destination="X", source="Y", path=[], info=info)
    msg = aprs.get_my_message("N0CALL-1", frame)
    print(f"Extracted message: {msg}")

if __name__ == "__main__":
    asyncio.run(main())

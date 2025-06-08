"""
Showcase: Send an APRS position report using DummyAPRS (sync)
"""
import asyncio
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    await aprs.connect()  # Synchronous connect for the dummy backend
    aprs.send_position_report(
        mycall="N0CALL-1",
        path=["WIDE1-1"],
        lat_dmm="5132.07N",
        long_dmm="00007.40W",
        symbol_id="/",
        symbol_code=">",
        comment="Test position",
        time_dhm="011234z"
    )
    print("Position report sent!")

if __name__ == "__main__":
    asyncio.run(main())

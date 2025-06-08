"""
Showcase: Send an APRS status report using DummyAPRS (sync)
"""
import asyncio
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    await aprs.connect()  # Synchronous connect for the dummy backend
    aprs.send_status_report(
        mycall="N0CALL-1",
        path=["WIDE1-1"],
        status="Net Control Center",
        time_dhm="092345z"
    )
    print("Status report sent!")

if __name__ == "__main__":
    asyncio.run(main())

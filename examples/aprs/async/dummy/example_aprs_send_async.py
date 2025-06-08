"""
Async Example: Send an APRS message using the Dummy backend.
"""
import asyncio
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    await aprs.connect()
    aprs.send_my_message_no_ack(
        mycall="N0CALL-1",
        path=["WIDE1-1"],
        recipient="DEST-1",
        message="Hello from Dummy APRS (async)!"
    )
    print("Message sent!")

if __name__ == "__main__":
    asyncio.run(main())

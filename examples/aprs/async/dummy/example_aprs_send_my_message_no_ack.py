"""
Showcase: Send an APRS message with no ACK using DummyAPRS (sync)
"""
import asyncio
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    await aprs.connect()  # Synchronous connect for the dummy backend
    aprs.send_my_message_no_ack(
        mycall="N0CALL-1",
        path=["WIDE1-1"],
        recipient="DEST-1",
        message="Hello, no ACK!"
    )
    print("Message sent (no ACK)")

if __name__ == "__main__":
    asyncio.run(main())

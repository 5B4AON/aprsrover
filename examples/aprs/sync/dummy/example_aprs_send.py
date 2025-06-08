"""
Example: Send an APRS message using the Dummy backend (synchronous).
"""
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs
import logging

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    # Example: send a message (no ACK)
    aprs.initialized = True
    aprs.send_my_message_no_ack(
        mycall="N0CALL-1",
        path=["WIDE1-1"],
        recipient="DEST-1",
        message="Hello from Dummy APRS!"
    )
    print("Message sent!")

if __name__ == "__main__":
    main()

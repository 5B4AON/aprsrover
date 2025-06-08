"""
Showcase: Send an APRS message and demonstrate ACK handling (sync)
"""
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs
from ax253 import Frame

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    aprs.initialized = True
    # Simulate sending a message with an ACK request
    info = b":N0CALL-1  :test{42"
    frame = Frame(destination="X", source="SRC", path=[], info=info)
    aprs.send_ack_if_requested(frame, "MYCALL-1", ["WIDE1-1"])
    print("ACK sent if requested.")

if __name__ == "__main__":
    main()

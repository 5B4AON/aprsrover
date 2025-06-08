"""
Showcase: Send an APRS message with an ACK request using DummyAPRS (sync)
"""
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs
from ax253 import Frame

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    aprs.initialized = True
    # Simulate sending a message with an ACK request (add {nn to info)
    info = b":DEST-1   :test with ack{42"
    frame = Frame(destination="X", source="Y", path=[], info=info)
    aprs.send_ack_if_requested(frame, "N0CALL-1", ["WIDE1-1"])
    print("ACK sent for message with ACK request.")

if __name__ == "__main__":
    main()

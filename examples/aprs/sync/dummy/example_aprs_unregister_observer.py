"""
Showcase: Unregister observer callback (sync)
"""
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs
from ax253 import Frame

logging.basicConfig(level=logging.DEBUG)

def cb(frame):
    print(f"Callback: {frame}")

def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    aprs.initialized = True
    aprs.register_observer("DEST-1", cb)
    aprs.unregister_observer("DEST-1", cb)
    # Simulate receiving a frame (should not call cb)
    info = b":DEST-1   :hello observer"
    frame = Frame(destination="X", source="Y", path=[], info=info)
    aprs._notify_observers(frame)
    print("Observer unregistered.")

if __name__ == "__main__":
    main()

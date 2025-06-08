"""
Showcase: Registering and using observer callbacks with DummyAPRS (sync)
"""
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs
from ax253 import Frame

logging.basicConfig(level=logging.DEBUG)

def my_observer(frame: Frame):
    print(f"Observer received frame: {frame}")

def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    aprs.initialized = True
    aprs.register_observer("DEST-1", my_observer)
    # Simulate receiving a frame
    info = b":DEST-1   :hello observer"
    frame = Frame(destination="X", source="Y", path=[], info=info)
    aprs._notify_observers(frame)

if __name__ == "__main__":
    main()

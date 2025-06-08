"""
Showcase: Send an APRS object report using DummyAPRS (sync)
"""
import logging
from examples.dummies import DummyAPRS
from aprsrover.aprs import Aprs

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    aprs.initialized = True
    aprs.send_object_report(
        mycall="N0CALL-1",
        path=["WIDE1-1"],
        time_dhm="011234z",
        lat_dmm="5132.07N",
        long_dmm="00007.40W",
        symbol_id="/",
        symbol_code=">",
        comment="Test object",
        name="OBJ1"
    )
    print("Object report sent!")

if __name__ == "__main__":
    main()

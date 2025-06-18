"""
Example: Send a compressed APRS position report.
"""
from aprsrover.aprs import Aprs
from examples.dummies import DummyAPRS

def main():
    aprs = Aprs(kiss=DummyAPRS())
    aprs.initialized = True
    aprs.kiss_protocol = aprs.kiss
    aprs.send_position_report(
        mycall="N0CALL-9",
        path=["WIDE1-1"],
        lat=40.7128,
        lon=-74.0060,
        symbol_id="/",
        symbol_code=">",
        comment="NYC compressed",
        time_dhm="011234z",
        compressed=True,
    )

if __name__ == "__main__":
    main()
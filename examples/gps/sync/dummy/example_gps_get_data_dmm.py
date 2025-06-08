"""
Showcase: Get GPS data in DMM format using DummyGPS (sync)
"""
import logging
from examples.dummies import DummyGPS
from aprsrover.gps import GPS

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    gps = GPS(gpsd=DummyGPS())
    data = gps.get_gps_data_dmm()
    print(f"GPS DMM data: {data}")

if __name__ == "__main__":
    main()

"""
Example: Get GPS position using the Dummy backend (synchronous).
"""
from examples.dummies import DummyGPSD
from aprsrover.gps import GPS
import logging

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    gps = GPS(gpsd=DummyGPSD())
    data = gps.get_gps_data_dmm()
    print(f"Current position: {data}")

if __name__ == "__main__":
    main()

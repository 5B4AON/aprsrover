"""
Example: Get GPS position using the Dummy backend (synchronous).
"""
from examples.dummies import DummyGPS
from aprsrover.gps import GPS, GPSError
import logging

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    gps = GPS(gpsd=DummyGPS())
    try:
        data = gps.get_gps_data_dmm()
        if data is None:
            print("No GPS fix yet. Try running: cgps -s")
        else:
            lat_dmm, lon_dmm, tm, bearing = data
            print("APRS DMM:", lat_dmm, lon_dmm, tm, bearing)
            lat_decimal, lon_decimal, tm_decimal, bearing_decimal = gps.get_gps_data_decimal()
            print("APRS Decimal:", lat_decimal, lon_decimal, tm_decimal, bearing_decimal)
    except GPSError as e:
        print(f"GPS error: {e}")

if __name__ == "__main__":
    main()

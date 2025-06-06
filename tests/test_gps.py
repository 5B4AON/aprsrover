import sys
import os
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aprsrover.gps import GPS, GPSError, GPSDInterface
from typing import Any, Optional, Tuple

class DummyPacket:
    def __init__(
        self,
        lat: float = 51.5345,
        lon: float = -0.1234,
        time: str = "2024-01-01T12:34:56.000Z",
        mode: int = 3,
        track: float = 123.4,
    ):
        self.lat = lat
        self.lon = lon
        self.time = time
        self.mode = mode
        self.track = track

class DummyGPSD(GPSDInterface):
    def __init__(self, packet: Optional[DummyPacket] = None, raise_exc: bool = False):
        self.packet = packet or DummyPacket()
        self.raise_exc = raise_exc
        self.calls = 0

    def get_current(self) -> Any:
        self.calls += 1
        if self.raise_exc:
            raise Exception("Dummy GPSD failure")
        return self.packet

class TestGPS(unittest.TestCase):

    def test_decimal_to_dmm_latitude(self):
        self.assertEqual(GPS.decimal_to_dmm(51.5345, True), "5132.07N")
        self.assertEqual(GPS.decimal_to_dmm(-51.5345, True), "5132.07S")

    def test_decimal_to_dmm_longitude(self):
        self.assertEqual(GPS.decimal_to_dmm(-0.1234, False), "00007.40W")
        self.assertEqual(GPS.decimal_to_dmm(0.1234, False), "00007.40E")

    def test_iso_to_ddhhmmz(self):
        self.assertEqual(GPS.iso_to_ddhhmmz("2024-01-01T12:34:56.000Z"), "011234z")

    def test_normalize_bearing(self):
        self.assertEqual(GPS.normalize_bearing(12.3), "012")
        self.assertEqual(GPS.normalize_bearing(359.9), "000")
        self.assertEqual(GPS.normalize_bearing(360.0), "000")
        self.assertEqual(GPS.normalize_bearing(180.6), "181")
        self.assertEqual(GPS.normalize_bearing(180.5), "180")

    def test_get_gps_data_dmm_success(self):
        gps = GPS(gpsd=DummyGPSD(DummyPacket(
            lat=51.5345, lon=-0.1234, time="2024-01-01T12:34:56.000Z", mode=3, track=123.4)))
        result = gps.get_gps_data_dmm()
        self.assertEqual(result, ("5132.07N", "00007.40W", "011234z", "123"))

    def test_get_gps_data_dmm_insufficient_mode(self):
        gps = GPS(gpsd=DummyGPSD(DummyPacket(mode=1)))
        result = gps.get_gps_data_dmm(max_attempts=1)
        self.assertIsNone(result)

    def test_get_gps_data_dmm_exception(self):
        gps = GPS(gpsd=DummyGPSD(raise_exc=True))
        with self.assertRaises(GPSError):
            gps.get_gps_data_dmm(max_attempts=1)

    def test_get_gps_data_decimal_success(self):
        gps = GPS(gpsd=DummyGPSD(DummyPacket(
            lat=51.5345, lon=-0.1234, time="2024-01-01T12:34:56.000Z", mode=3, track=123.4)))
        result = gps.get_gps_data_decimal()
        self.assertEqual(result, (51.5345, -0.1234, "2024-01-01T12:34:56.000Z", 123.4))

    def test_get_gps_data_decimal_insufficient_mode(self):
        gps = GPS(gpsd=DummyGPSD(DummyPacket(mode=1)))
        result = gps.get_gps_data_decimal(max_attempts=1)
        self.assertIsNone(result)

    def test_get_gps_data_decimal_exception(self):
        gps = GPS(gpsd=DummyGPSD(raise_exc=True))
        with self.assertRaises(GPSError):
            gps.get_gps_data_decimal(max_attempts=1)

if __name__ == "__main__":
    unittest.main()

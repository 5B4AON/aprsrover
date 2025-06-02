import sys
import os
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aprsrover.gps import GPS, GPSError

class DummyPacket:
    def __init__(self, lat=0.0, lon=0.0, time="2024-01-01T12:00:00.000Z", mode=1, track=0.0):
        self.lat = lat
        self.lon = lon
        self.time = time
        self.mode = mode
        self.track = track

class DummyGPSD:
    def __init__(self, packet_or_exception):
        self.packet_or_exception = packet_or_exception

    def get_current(self):
        if isinstance(self.packet_or_exception, Exception):
            raise self.packet_or_exception
        return self.packet_or_exception

class TestGPS(unittest.TestCase):
    def setUp(self):
        self.gps = GPS()

    def test_decimal_to_dmm_latitude(self):
        self.assertEqual(self.gps.decimal_to_dmm(51.5, True), '5130.00N')
        self.assertEqual(self.gps.decimal_to_dmm(-51.5, True), '5130.00S')

    def test_decimal_to_dmm_longitude(self):
        self.assertEqual(self.gps.decimal_to_dmm(0.5, False), '00030.00E')
        self.assertEqual(self.gps.decimal_to_dmm(-0.5, False), '00030.00W')

    def test_iso_to_ddhhmmz(self):
        self.assertEqual(self.gps.iso_to_ddhhmmz('2025-06-01T12:34:56.000Z'), '011234z')

    def test_normalize_bearing(self):
        self.assertEqual(self.gps.normalize_bearing(0.0), '000')
        self.assertEqual(self.gps.normalize_bearing(12.3), '012')
        self.assertEqual(self.gps.normalize_bearing(359.9), '000')
        self.assertEqual(self.gps.normalize_bearing(360.0), '000')
        self.assertEqual(self.gps.normalize_bearing(180.6), '181')
        self.assertEqual(self.gps.normalize_bearing(180.5), '180')

    def test_get_gps_data_dmm_success(self):
        gps = GPS()
        gps.gpsd = DummyGPSD(DummyPacket(
            lat=51.5345, lon=-0.1234, time="2024-01-01T12:34:56.000Z", mode=3, track=123.4))
        gps.connected = True
        result = gps.get_gps_data_dmm()
        self.assertEqual(result, ("5132.07N", "00007.40W", "011234z", "123"))

    def test_get_gps_data_decimal_success(self):
        gps = GPS()
        gps.gpsd = DummyGPSD(DummyPacket(
            lat=51.5345, lon=-0.1234, time="2024-01-01T12:34:56.000Z", mode=3, track=123.4))
        gps.connected = True
        result = gps.get_gps_data_decimal()
        self.assertEqual(result, (51.5345, -0.1234, "2024-01-01T12:34:56.000Z", 123.4))

    def test_get_gps_data_none(self):
        gps = GPS()
        gps.gpsd = DummyGPSD(DummyPacket(lat=0.0, lon=0.0, mode=1, track=0.0))
        gps.connected = True
        result = gps.get_gps_data_dmm(max_attempts=2)
        self.assertIsNone(result)
        result2 = gps.get_gps_data_decimal(max_attempts=2)
        self.assertIsNone(result2)

    def test_get_gps_data_exception(self):
        gps = GPS()
        gps.gpsd = DummyGPSD(Exception("GPSD error"))
        gps.connected = True
        with self.assertRaises(GPSError):
            gps.get_gps_data_dmm(max_attempts=2)
        with self.assertRaises(GPSError):
            gps.get_gps_data_decimal(max_attempts=2)

    def test_connect_failure(self):
        gps = GPS()
        import gpsd as gpsd_module
        orig_connect = gpsd_module.connect
        gpsd_module.connect = lambda: (_ for _ in ()).throw(Exception("fail"))
        with self.assertRaises(GPSError):
            gps.connect()
        gpsd_module.connect = orig_connect

if __name__ == '__main__':
    unittest.main()

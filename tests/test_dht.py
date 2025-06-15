import unittest
from aprsrover.dht import DHT, DHTError, DummyDHTBackend

class TestDummyDHTBackend(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = DummyDHTBackend()

    def test_read(self):
        temp, humidity = self.backend.read()
        self.assertIsInstance(temp, float)
        self.assertIsInstance(humidity, float)
        self.assertGreaterEqual(temp, -50.0)
        self.assertLessEqual(temp, 100.0)
        self.assertGreaterEqual(humidity, 0.0)
        self.assertLessEqual(humidity, 100.0)

class TestDHTWithDummy(unittest.TestCase):
    def setUp(self) -> None:
        self.dht = DHT(sensor_type='DHT22', pin=4, backend=DummyDHTBackend())

    def test_read(self):
        temp, humidity = self.dht.read()
        self.assertEqual((temp, humidity), (22.5, 55.0))

    def test_monitor(self):
        gen = self.dht.monitor(interval=0.01)
        for _ in range(3):
            temp, humidity = next(gen)
            self.assertEqual((temp, humidity), (22.5, 55.0))

    def test_monitor_async(self):
        import asyncio
        async def run_monitor():
            count = 0
            async for temp, humidity in self.dht.monitor_async(interval=0.01):
                self.assertEqual((temp, humidity), (22.5, 55.0))
                count += 1
                if count >= 3:
                    break
        asyncio.run(run_monitor())

    def test_invalid_sensor_type(self):
        dht = DHT(sensor_type='INVALID', pin=4, backend=DummyDHTBackend())
        # Should not raise, since dummy backend is used
        dht.read()

    def test_no_backend_import_error(self):
        # Only run if Adafruit_DHT is not installed
        try:
            import Adafruit_DHT
            has_adafruit = True
        except ImportError:
            has_adafruit = False
        if not has_adafruit:
            with self.assertRaises(DHTError):
                DHT(sensor_type='DHT22', pin=4, backend=None).read()

if __name__ == "__main__":
    unittest.main()

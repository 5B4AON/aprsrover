import unittest
from aprsrover.compass import Compass, CompassError, DummyCompassBackend

class TestDummyCompassBackend(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = DummyCompassBackend()

    def test_read(self):
        heading = self.backend.read()
        self.assertIsInstance(heading, float)
        self.assertGreaterEqual(heading, 0.0)
        self.assertLessEqual(heading, 360.0)

class TestCompassWithDummy(unittest.TestCase):
    def setUp(self) -> None:
        self.compass = Compass(backend=DummyCompassBackend())

    def test_read(self):
        heading = self.compass.read()
        self.assertEqual(heading, 123.4)

    def test_monitor(self):
        gen = self.compass.monitor(interval=0.01)
        for _ in range(3):
            heading = next(gen)
            self.assertEqual(heading, 123.4)

    def test_monitor_async(self):
        import asyncio
        async def run_monitor():
            count = 0
            async for heading in self.compass.monitor_async(interval=0.01):
                self.assertEqual(heading, 123.4)
                count += 1
                if count >= 3:
                    break
        asyncio.run(run_monitor())

    def test_no_backend_import_error(self):
        # Only run if smbus2 is not installed
        try:
            import smbus2
            has_smbus2 = True
        except ImportError:
            has_smbus2 = False
        if not has_smbus2:
            with self.assertRaises(CompassError):
                Compass(backend=None).read()

if __name__ == "__main__":
    unittest.main()

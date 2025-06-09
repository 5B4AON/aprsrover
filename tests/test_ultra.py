import unittest
import threading
import time
import asyncio
from aprsrover.ultra import UltraSonic, UltraSonicError, UltraSonicEvent, GPIOInterface
from typing import Optional

class DummyGPIO:
    BCM = 'BCM'
    IN = 'IN'
    OUT = 'OUT'
    LOW = 0
    HIGH = 1
    def __init__(self):
        self.pin_modes = {}
        self.pin_values = {}
        self.cleanup_calls = []
        self.triggered = threading.Event()
        self.echo_high = False
        self.input_calls = 0
    def setmode(self, mode):
        self.mode = mode
    def setup(self, pin, mode):
        self.pin_modes[pin] = mode
        self.pin_values[pin] = self.LOW
    def output(self, pin, value):
        self.pin_values[pin] = value
        if pin == 23 and value == self.HIGH:
            self.triggered.set()
    def input(self, pin):
        # Simulate echo pin behavior for 100 cm
        if pin == 24:
            now = time.time()
            if not hasattr(self, "_pulse_start"):
                self._pulse_start = now
            pulse_duration = (100 * 2) / 34300  # 100 cm
            if now - self._pulse_start < pulse_duration:
                return self.HIGH
            else:
                return self.LOW
        return self.LOW
    def cleanup(self, pin: Optional[int] = None):
        self.cleanup_calls.append(pin)

class TestUltraSonic(unittest.TestCase):
    def setUp(self):
        self.gpio = DummyGPIO()
        self.ultra = UltraSonic(trigger_pin=23, echo_pin=24, gpio=self.gpio, timeout=0.05)

    def test_measure_distance_success(self):
        called = []
        def observer(event):
            called.append(event.distance_cm)
        self.ultra.add_observer(observer)
        dist = self.ultra.measure_distance()
        self.assertIsInstance(dist, float)
        self.assertTrue(0 < dist < 1000)
        self.assertTrue(called)
        self.ultra.remove_observer(observer)

    def test_measure_distance_timeout_high(self):
        # Simulate never getting echo HIGH
        self.gpio.input_calls = 1000
        def always_low(pin): return DummyGPIO.LOW
        self.gpio.input = always_low
        with self.assertRaises(UltraSonicError):
            self.ultra.measure_distance()

    def test_measure_distance_timeout_low(self):
        # Simulate echo HIGH but never LOW
        calls = [0]
        def echo_high_then_stuck(pin):
            calls[0] += 1
            if calls[0] == 1:
                return DummyGPIO.LOW
            return DummyGPIO.HIGH
        self.gpio.input = echo_high_then_stuck
        with self.assertRaises(UltraSonicError):
            self.ultra.measure_distance()

    def test_add_and_remove_observer(self):
        def obs(event): pass
        self.ultra.add_observer(obs)
        self.assertIn(obs, self.ultra._observers)
        self.ultra.remove_observer(obs)
        self.assertNotIn(obs, self.ultra._observers)

    def test_start_and_stop_monitoring(self):
        self.ultra.start_monitoring(interval=0.01)
        time.sleep(0.05)
        self.ultra.stop_monitoring()
        self.assertFalse(self.ultra._monitoring.is_set())
        # Should be able to start again
        self.ultra.start_monitoring(interval=0.01)
        self.ultra.stop_monitoring()

    def test_cleanup(self):
        self.ultra.cleanup()
        self.assertIn(23, self.gpio.cleanup_calls)
        self.assertIn(24, self.gpio.cleanup_calls)

    def test_async_measure_distance(self):
        async def run():
            dist = await self.ultra.measure_distance_async()
            self.assertIsInstance(dist, float)
        asyncio.run(run())

    def test_async_monitor(self):
        called = []
        def observer(event):
            called.append(event.distance_cm)
        self.ultra.add_observer(observer)
        async def run():
            task = asyncio.create_task(self.ultra.async_monitor(interval=0.01))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        asyncio.run(run())
        self.assertTrue(called)

if __name__ == "__main__":
    unittest.main()

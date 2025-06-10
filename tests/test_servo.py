"""
Unit tests for aprsrover.servo module.

Covers:
- Servo angle setting (instant and smooth)
- Input validation
- Exception handling
- Async API

Mocks hardware access for testability.
"""

import sys
import os
import unittest
import asyncio
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aprsrover.servo import Servo, ServoError, PWMControllerInterface

class DummyPWM(PWMControllerInterface):
    def __init__(self):
        self.calls = []
        self.freq = None

    def set_pwm(self, channel: int, on: int, off: int) -> None:
        self.calls.append((channel, on, off))

    def set_pwm_freq(self, freq: int) -> None:
        self.freq = freq

class TestServo(unittest.TestCase):
    def setUp(self) -> None:
        self.dummy_pwm = DummyPWM()
        self.servo = Servo(channel=2, pwm=self.dummy_pwm, angle_min=10, angle_max=170, pwm_min=200, pwm_max=500)

    def test_init_success(self):
        # No explicit initialized flag, but should not raise
        self.assertEqual(self.dummy_pwm.freq, 50)

    def test_set_angle_instant(self):
        self.servo.set_angle(90)
        self.assertAlmostEqual(self.servo.get_angle(), 90, places=6)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.servo._angle_to_pwm(90))

    def test_set_angle_clamping(self):
        self.servo.set_angle(-100)
        self.assertEqual(self.servo.get_angle(), self.servo.angle_min)
        self.servo.set_angle(999)
        self.assertEqual(self.servo.get_angle(), self.servo.angle_max)

    def test_set_angle_smooth(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.servo.set_angle(20, speed=40, step=10)
        self.assertAlmostEqual(self.servo.get_angle(), 20, places=6)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.servo._angle_to_pwm(20))
        time.sleep = orig_sleep

    def test_set_angle_invalid_input(self):
        self.servo.set_angle("notanumber")
        self.assertEqual(self.servo.get_angle(), self.servo.angle_min)

    def test_set_angle_pwm_exception(self):
        def fail_set_pwm(channel, on, off):
            raise RuntimeError("fail")
        self.servo.pwm.set_pwm = fail_set_pwm
        with self.assertRaises(ServoError):
            self.servo.set_angle(30)

    def test_pwm_interface_protocol(self):
        class DummyPWM2:
            def set_pwm(self, channel: int, on: int, off: int) -> None:
                pass
        s = Servo(channel=0, pwm=DummyPWM2())
        s.set_angle(45)

    def test_angle_to_pwm_range(self):
        # Check PWM values at min and max
        self.assertEqual(self.servo._angle_to_pwm(self.servo.angle_min), self.servo.pwm_min)
        self.assertEqual(self.servo._angle_to_pwm(self.servo.angle_max), self.servo.pwm_max)

    def test_async_set_angle_instant(self):
        async def runner():
            await self.servo.set_angle_async(60)
            self.assertAlmostEqual(self.servo.get_angle(), 60, places=6)
            self.assertEqual(self.dummy_pwm.calls[-1][2], self.servo._angle_to_pwm(60))
        asyncio.run(runner())

    def test_async_set_angle_smooth(self):
        async def runner():
            orig_sleep = asyncio.sleep
            async def fake_sleep(x): return None
            asyncio.sleep = fake_sleep
            await self.servo.set_angle_async(30, speed=10, step=10)
            self.assertAlmostEqual(self.servo.get_angle(), 30, places=6)
            self.assertEqual(self.dummy_pwm.calls[-1][2], self.servo._angle_to_pwm(30))
            asyncio.sleep = orig_sleep
        asyncio.run(runner())

    def test_async_set_angle_cancel(self):
        async def runner():
            orig_sleep = asyncio.sleep
            async def fake_sleep(x): return None
            asyncio.sleep = fake_sleep
            task = asyncio.create_task(self.servo.set_angle_async(170, speed=1, step=1, step_interval=0.01))
            await asyncio.sleep(0.02)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            self.assertLessEqual(self.servo.get_angle(), 170)
            asyncio.sleep = orig_sleep
        asyncio.run(runner())

if __name__ == "__main__":
    unittest.main()
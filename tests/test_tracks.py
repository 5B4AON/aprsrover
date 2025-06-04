import sys
import os
import unittest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aprsrover.tracks import Tracks, TracksError, PWMControllerInterface

class DummyPWM(PWMControllerInterface):
    def __init__(self):
        self.calls = []
        self.freq = None

    def set_pwm(self, channel: int, on: int, off: int) -> None:
        self.calls.append((channel, on, off))

    def set_pwm_freq(self, freq: int) -> None:
        self.freq = freq

class TestTracks(unittest.TestCase):
    """
    Unit tests for the Tracks class using DummyPWM.
    """

    def setUp(self) -> None:
        """Set up a DummyPWM controller for each test."""
        self.dummy_pwm = DummyPWM()
        self.tracks = Tracks(pwm=self.dummy_pwm)

    def test_init_success(self):
        self.assertTrue(self.tracks.initialized)

    def test_init_failure(self):
        class FailingPWM(DummyPWM):
            def set_pwm_freq(self, freq: int) -> None:
                raise Exception("fail")
        with self.assertRaises(TracksError):
            Tracks(pwm=FailingPWM())

    def test_get_pwm_fw_speed(self) -> None:
        self.assertEqual(Tracks.get_pwm_fw_speed(0), Tracks.PWM_STOP)
        self.assertEqual(Tracks.get_pwm_fw_speed(100), Tracks.PWM_FW_MAX)
        self.assertEqual(Tracks.get_pwm_fw_speed(50), Tracks.PWM_FW_MIN - round((50 * 90) / 100))

    def test_get_pwm_rev_speed(self) -> None:
        self.assertEqual(Tracks.get_pwm_rev_speed(0), Tracks.PWM_STOP)
        self.assertEqual(Tracks.get_pwm_rev_speed(100), Tracks.PWM_REV_MAX)
        self.assertEqual(Tracks.get_pwm_rev_speed(50), Tracks.PWM_REV_MIN + round((50 * 90) / 100))

    def test_set_right_track_speed_forward(self) -> None:
        self.tracks.set_right_track_speed(60)
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_fw_speed(60)),
            self.dummy_pwm.calls
        )

    def test_set_right_track_speed_reverse(self) -> None:
        self.tracks.set_right_track_speed(-40)
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_rev_speed(40)),
            self.dummy_pwm.calls
        )

    def test_set_left_track_speed_forward(self) -> None:
        self.tracks.set_left_track_speed(80)
        self.assertIn(
            (Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(80)),
            self.dummy_pwm.calls
        )

    def test_set_left_track_speed_reverse(self) -> None:
        self.tracks.set_left_track_speed(-30)
        self.assertIn(
            (Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_rev_speed(30)),
            self.dummy_pwm.calls
        )

    def test_pwm_freq_set(self) -> None:
        self.assertEqual(self.dummy_pwm.freq, 50)

    def test_speed_below_min(self) -> None:
        self.tracks.set_right_track_speed(-150)
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_rev_speed(100)),
            self.dummy_pwm.calls
        )

    def test_speed_above_max(self) -> None:
        self.tracks.set_left_track_speed(150)
        self.assertIn(
            (Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(100)),
            self.dummy_pwm.calls
        )

    def test_non_integer_speed(self) -> None:
        self.tracks.set_right_track_speed(42.7)
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_fw_speed(42)),
            self.dummy_pwm.calls
        )
        self.tracks.set_left_track_speed("55")
        self.assertIn(
            (Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(55)),
            self.dummy_pwm.calls
        )

    def test_invalid_speed_type(self) -> None:
        self.tracks.set_right_track_speed(None)
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_fw_speed(0)),
            self.dummy_pwm.calls
        )

    def test_sanitize_duration_valid(self):
        self.assertEqual(self.tracks.sanitize_duration(1.234), 1.23)
        self.assertEqual(self.tracks.sanitize_duration(0.015), 0.01)
        self.assertEqual(self.tracks.sanitize_duration(0.016), 0.02)
        self.assertEqual(self.tracks.sanitize_duration(10), 10.0)
        self.assertEqual(self.tracks.sanitize_duration("2.5"), 2.5)

    def test_sanitize_duration_invalid(self):
        with self.assertRaises(TracksError):
            self.tracks.sanitize_duration(0)
        with self.assertRaises(TracksError):
            self.tracks.sanitize_duration(-5)
        with self.assertRaises(TracksError):
            self.tracks.sanitize_duration("abc")
        with self.assertRaises(TracksError):
            self.tracks.sanitize_duration(None)
        with self.assertRaises(TracksError):
            self.tracks.sanitize_duration(11)  # Exceeds MOVE_DURATION_MAX

    def test_move_valid(self):
        import time as _time
        orig_sleep = _time.sleep
        _time.sleep = lambda x: None  # Patch sleep to avoid delay
        self.tracks.move(50, -50, 0.5)
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)
        _time.sleep = orig_sleep

    def test_move_invalid_duration(self):
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, 0)
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, -1)
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, "bad")
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, 15)  # Exceeds MOVE_DURATION_MAX

    def test_move_speed_clamping(self):
        import time as _time
        orig_sleep = _time.sleep
        _time.sleep = lambda x: None
        self.tracks.move(150, -150, 1)
        self.assertIn(
            (Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(100)),
            self.dummy_pwm.calls
        )
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_rev_speed(100)),
            self.dummy_pwm.calls
        )
        _time.sleep = orig_sleep

    def test_move_accel_none_and_zero(self):
        import time as _time
        orig_sleep = _time.sleep
        _time.sleep = lambda x: None
        # accel=None
        self.tracks.move(10, 10, 0.2, accel=None)
        # accel=0
        self.tracks.move(10, 10, 0.2, accel=0)
        _time.sleep = orig_sleep

    def test_move_accel_negative_and_too_high(self):
        import time as _time
        orig_sleep = _time.sleep
        _time.sleep = lambda x: None
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, 1, accel=-1)
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, 1, accel=2000)
        _time.sleep = orig_sleep

    def test_move_accel_interval_invalid(self):
        import time as _time
        orig_sleep = _time.sleep
        _time.sleep = lambda x: None
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, 1, accel=10, accel_interval=0)
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, 1, accel=10, accel_interval=2)
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, 1, accel=10, accel_interval="bad")
        _time.sleep = orig_sleep

    def test_move_accel_smoothing(self):
        import time as _time
        orig_sleep = _time.sleep
        _time.sleep = lambda x: None
        # Should ramp up and then hold
        self.tracks.move(0, 0, 0.2, accel=100, accel_interval=0.05)
        self.tracks.move(0, 50, 0.2, accel=50, accel_interval=0.05)
        _time.sleep = orig_sleep

    def test_move_async_normal(self):
        async def runner():
            await self.tracks.move_async(80, -80, 0.1)
            self.assertEqual(self.tracks.get_left_track_speed(), 0)
            self.assertEqual(self.tracks.get_right_track_speed(), 0)
        asyncio.run(runner())

    def test_move_async_cancel(self):
        async def runner():
            task = asyncio.create_task(self.tracks.move_async(80, 80, 1))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                # After cancel, tracks should still be running at last set speed
                self.assertEqual(self.tracks.get_left_track_speed(), 80)
                self.assertEqual(self.tracks.get_right_track_speed(), 80)
                # Now stop them manually
                self.tracks.set_left_track_speed(0)
                self.tracks.set_right_track_speed(0)
                self.assertEqual(self.tracks.get_left_track_speed(), 0)
                self.assertEqual(self.tracks.get_right_track_speed(), 0)
        asyncio.run(runner())

    def test_move_async_accel_none_and_zero(self):
        async def runner():
            await self.tracks.move_async(10, 10, 0.2, accel=None)
            await self.tracks.move_async(10, 10, 0.2, accel=0)
        asyncio.run(runner())

    def test_move_async_accel_negative_and_too_high(self):
        async def runner():
            with self.assertRaises(TracksError):
                await self.tracks.move_async(10, 10, 1, accel=-1)
            with self.assertRaises(TracksError):
                await self.tracks.move_async(10, 10, 1, accel=2000)
        asyncio.run(runner())

    def test_move_async_accel_interval_invalid(self):
        async def runner():
            with self.assertRaises(TracksError):
                await self.tracks.move_async(10, 10, 1, accel=10, accel_interval=0)
            with self.assertRaises(TracksError):
                await self.tracks.move_async(10, 10, 1, accel=10, accel_interval=2)
            with self.assertRaises(TracksError):
                await self.tracks.move_async(10, 10, 1, accel=10, accel_interval="bad")
        asyncio.run(runner())

    def test_move_async_accel_smoothing(self):
        async def runner():
            await self.tracks.move_async(0, 0, 0.2, accel=100, accel_interval=0.05)
            await self.tracks.move_async(0, 50, 0.2, accel=50, accel_interval=0.05)
        asyncio.run(runner())

if __name__ == "__main__":
    unittest.main()

import sys
import os
import unittest
import asyncio
import time

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
    def setUp(self) -> None:
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

    def test_get_pwm_fw_speed(self):
        self.assertEqual(Tracks.get_pwm_fw_speed(0), Tracks.PWM_STOP)
        self.assertEqual(Tracks.get_pwm_fw_speed(100), Tracks.PWM_FW_MAX)
        self.assertEqual(Tracks.get_pwm_fw_speed(50), Tracks.PWM_FW_MIN - round((50 * 90) / 100))

    def test_get_pwm_rev_speed(self):
        self.assertEqual(Tracks.get_pwm_rev_speed(0), Tracks.PWM_STOP)
        self.assertEqual(Tracks.get_pwm_rev_speed(100), Tracks.PWM_REV_MAX)
        self.assertEqual(Tracks.get_pwm_rev_speed(50), Tracks.PWM_REV_MIN + round((50 * 90) / 100))

    def test_set_left_track_speed_forward(self):
        self.tracks.set_left_track_speed(80)
        self.assertIn(
            (Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(80)),
            self.dummy_pwm.calls
        )

    def test_set_left_track_speed_reverse(self):
        self.tracks.set_left_track_speed(-30)
        self.assertIn(
            (Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_rev_speed(30)),
            self.dummy_pwm.calls
        )

    def test_set_right_track_speed_forward(self):
        self.tracks.set_right_track_speed(60)
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_fw_speed(60)),
            self.dummy_pwm.calls
        )

    def test_set_right_track_speed_reverse(self):
        self.tracks.set_right_track_speed(-40)
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_rev_speed(40)),
            self.dummy_pwm.calls
        )

    def test_pwm_freq_set(self):
        self.assertEqual(self.dummy_pwm.freq, 50)

    def test_speed_below_min(self):
        self.tracks.set_right_track_speed(-150)
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_rev_speed(100)),
            self.dummy_pwm.calls
        )

    def test_speed_above_max(self):
        self.tracks.set_left_track_speed(150)
        self.assertIn(
            (Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(100)),
            self.dummy_pwm.calls
        )

    def test_non_integer_speed(self):
        self.tracks.set_left_track_speed("75.5")
        self.assertIn(
            (Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(75)),
            self.dummy_pwm.calls
        )

    def test_invalid_speed_type(self):
        self.tracks.set_right_track_speed(None)
        self.assertIn(
            (Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_fw_speed(0)),
            self.dummy_pwm.calls
        )

    def test_get_left_right_track_speed(self):
        self.tracks.set_left_track_speed(33)
        self.tracks.set_right_track_speed(-44)
        self.assertEqual(self.tracks.get_left_track_speed(), 33)
        self.assertEqual(self.tracks.get_right_track_speed(), -44)

    def test_sanitize_duration_valid(self):
        self.assertEqual(self.tracks.sanitize_duration(1.234), 1.23)
        self.assertEqual(self.tracks.sanitize_duration(0.015), 0.01)
        self.assertEqual(self.tracks.sanitize_duration(0.016), 0.02)
        self.assertEqual(self.tracks.sanitize_duration(10), 10.0)

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

    def test_move_no_accel_stop(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.set_left_track_speed(0)
        self.tracks.set_right_track_speed(0)
        self.tracks.move(50, -50, 0.1, stop_at_end=True)
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)
        time.sleep = orig_sleep

    def test_move_no_accel_no_stop(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.set_left_track_speed(0)
        self.tracks.set_right_track_speed(0)
        self.tracks.move(50, -50, 0.1, stop_at_end=False)
        self.assertEqual(self.tracks.get_left_track_speed(), 50)
        self.assertEqual(self.tracks.get_right_track_speed(), -50)
        time.sleep = orig_sleep

    def test_move_with_accel_stop(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.set_left_track_speed(10)
        self.tracks.set_right_track_speed(-10)
        self.tracks.move(50, -50, 0.2, accel=100, accel_interval=0.05, stop_at_end=True)
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)
        time.sleep = orig_sleep

    def test_move_with_accel_no_stop(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.set_left_track_speed(10)
        self.tracks.set_right_track_speed(-10)
        self.tracks.move(50, -50, 0.2, accel=100, accel_interval=0.05, stop_at_end=False)
        self.assertEqual(self.tracks.get_left_track_speed(), 50)
        self.assertEqual(self.tracks.get_right_track_speed(), -50)
        time.sleep = orig_sleep

    def test_move_invalid_accel(self):
        with self.assertRaises(TracksError):
            self.tracks.move(50, 50, 1, accel=-10)
        with self.assertRaises(TracksError):
            self.tracks.move(50, 50, 1, accel=2000)
        with self.assertRaises(TracksError):
            self.tracks.move(50, 50, 1, accel_interval=0)

    def test_turn_spin_in_place_duration(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.turn(50, 0, 'left', duration=1, stop_at_end=True)
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)
        time.sleep = orig_sleep

    def test_turn_spin_in_place_angle(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.turn(70, 0, 'right', angle_deg=180, stop_at_end=True)
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)
        time.sleep = orig_sleep

    def test_turn_arc_duration(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.turn(60, 20, 'left', duration=1.5, stop_at_end=True)
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)
        time.sleep = orig_sleep

    def test_turn_arc_angle(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.turn(80, 25, 'right', angle_deg=90, stop_at_end=True)
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)
        time.sleep = orig_sleep

    def test_turn_no_stop(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.turn(60, 20, 'left', duration=1.5, stop_at_end=False)
        # Should leave tracks running at last speed
        left, right = self.tracks._track_speeds_for_turn(60, 20, 'left')
        self.assertEqual(self.tracks.get_left_track_speed(), left)
        self.assertEqual(self.tracks.get_right_track_speed(), right)
        time.sleep = orig_sleep

    def test_turn_invalid_direction(self):
        with self.assertRaises(TracksError):
            self.tracks.turn(50, 0, 'up', duration=1)

    def test_turn_zero_speed(self):
        with self.assertRaises(TracksError):
            self.tracks.turn(0, 10, 'left', duration=1)

    def test_turn_negative_radius(self):
        with self.assertRaises(TracksError):
            self.tracks.turn(50, -5, 'right', duration=1)

    def test_turn_both_duration_and_angle(self):
        with self.assertRaises(TracksError):
            self.tracks.turn(50, 10, 'left', duration=1, angle_deg=90)

    def test_turn_neither_duration_nor_angle(self):
        with self.assertRaises(TracksError):
            self.tracks.turn(50, 10, 'left')

    def test__track_speeds_for_turn_spin_left(self):
        left, right = self.tracks._track_speeds_for_turn(70, 0, "left")
        self.assertEqual(left, -70)
        self.assertEqual(right, 70)

    def test__track_speeds_for_turn_spin_right(self):
        left, right = self.tracks._track_speeds_for_turn(70, 0, "right")
        self.assertEqual(left, 70)
        self.assertEqual(right, -70)

    def test__track_speeds_for_turn_arc_left(self):
        left, right = self.tracks._track_speeds_for_turn(70, 20, "left")
        self.assertLess(left, right)

    def test__track_speeds_for_turn_arc_right(self):
        left, right = self.tracks._track_speeds_for_turn(70, 20, "right")
        self.assertLess(right, left)

    def test__turn_duration_for_angle_straight(self):
        duration = self.tracks._turn_duration_for_angle(70, 1000, 180)
        self.assertGreater(duration, 0)

    def test__turn_duration_for_angle_spin(self):
        duration = self.tracks._turn_duration_for_angle(70, 0, 360)
        self.assertGreater(duration, 0)

    def test__turn_duration_for_angle_zero_speed(self):
        with self.assertRaises(TracksError):
            self.tracks._turn_duration_for_angle(0, 10, 90)

    def test_stop(self):
        self.tracks.set_left_track_speed(50)
        self.tracks.set_right_track_speed(-50)
        self.tracks.stop()
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)

    def test_move_async_no_accel_stop(self):
        async def runner():
            orig_sleep = asyncio.sleep
            async def fake_sleep(x): return None
            asyncio.sleep = fake_sleep
            self.tracks.set_left_track_speed(0)
            self.tracks.set_right_track_speed(0)
            await self.tracks.move_async(50, -50, 0.1, stop_at_end=True)
            self.assertEqual(self.tracks.get_left_track_speed(), 0)
            self.assertEqual(self.tracks.get_right_track_speed(), 0)
            asyncio.sleep = orig_sleep
        asyncio.run(runner())

    def test_move_async_no_accel_no_stop(self):
        async def runner():
            orig_sleep = asyncio.sleep
            async def fake_sleep(x): return None
            asyncio.sleep = fake_sleep
            self.tracks.set_left_track_speed(0)
            self.tracks.set_right_track_speed(0)
            await self.tracks.move_async(50, -50, 0.1, stop_at_end=False)
            self.assertEqual(self.tracks.get_left_track_speed(), 50)
            self.assertEqual(self.tracks.get_right_track_speed(), -50)
            asyncio.sleep = orig_sleep
        asyncio.run(runner())

    def test_move_async_with_accel_stop(self):
        async def runner():
            orig_sleep = asyncio.sleep
            async def fake_sleep(x): return None
            asyncio.sleep = fake_sleep
            self.tracks.set_left_track_speed(10)
            self.tracks.set_right_track_speed(-10)
            await self.tracks.move_async(50, -50, 0.2, accel=100, accel_interval=0.05, stop_at_end=True)
            self.assertEqual(self.tracks.get_left_track_speed(), 0)
            self.assertEqual(self.tracks.get_right_track_speed(), 0)
            asyncio.sleep = orig_sleep
        asyncio.run(runner())

    def test_move_async_with_accel_no_stop(self):
        async def runner():
            orig_sleep = asyncio.sleep
            async def fake_sleep(x): return None
            asyncio.sleep = fake_sleep
            self.tracks.set_left_track_speed(10)
            self.tracks.set_right_track_speed(-10)
            await self.tracks.move_async(50, -50, 0.2, accel=100, accel_interval=0.05, stop_at_end=False)
            self.assertEqual(self.tracks.get_left_track_speed(), 50)
            self.assertEqual(self.tracks.get_right_track_speed(), -50)
            asyncio.sleep = orig_sleep
        asyncio.run(runner())

    def test_turn_async_spin_in_place_angle(self):
        async def runner():
            orig_sleep = asyncio.sleep
            async def fake_sleep(x): return None
            asyncio.sleep = fake_sleep
            await self.tracks.turn_async(70, 0, 'left', angle_deg=90, stop_at_end=True)
            self.assertEqual(self.tracks.get_left_track_speed(), 0)
            self.assertEqual(self.tracks.get_right_track_speed(), 0)
            asyncio.sleep = orig_sleep
        asyncio.run(runner())

    def test_turn_async_arc_duration(self):
        async def runner():
            orig_sleep = asyncio.sleep
            async def fake_sleep(x): return None
            asyncio.sleep = fake_sleep
            await self.tracks.turn_async(60, 15, 'right', duration=1.0, stop_at_end=True)
            self.assertEqual(self.tracks.get_left_track_speed(), 0)
            self.assertEqual(self.tracks.get_right_track_speed(), 0)
            asyncio.sleep = orig_sleep
        asyncio.run(runner())

    def test_turn_async_no_stop(self):
        async def runner():
            orig_sleep = asyncio.sleep
            async def fake_sleep(x): return None
            asyncio.sleep = fake_sleep
            await self.tracks.turn_async(60, 15, 'right', duration=1.0, stop_at_end=False)
            left, right = self.tracks._track_speeds_for_turn(60, 15, 'right')
            self.assertEqual(self.tracks.get_left_track_speed(), left)
            self.assertEqual(self.tracks.get_right_track_speed(), right)
            asyncio.sleep = orig_sleep
        asyncio.run(runner())

if __name__ == "__main__":
    unittest.main()

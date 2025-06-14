import sys
import os
import unittest
import time
import logging
import asyncio

logging.basicConfig(level=logging.WARNING)

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
        self.assertEqual(self.tracks.pwm_fw_min, Tracks.DEFAULT_PWM_FW_MIN)
        self.assertEqual(self.tracks.left_channel, Tracks.DEFAULT_LEFT_CHANNEL)
        self.assertEqual(self.tracks.left_channel_reverse, Tracks.DEFAULT_LEFT_CHANNEL_REVERSE)

    def test_init_failure(self):
        class FailingPWM(DummyPWM):
            def set_pwm_freq(self, freq: int) -> None:
                raise RuntimeError("fail")
        with self.assertRaises(TracksError):
            Tracks(pwm=FailingPWM())

    def test_set_left_track_speed(self):
        self.tracks.left_channel_reverse = False
        self.tracks.set_left_track_speed(50)
        self.assertEqual(self.tracks.get_left_track_speed(), 50)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_fw_speed(50))

        self.tracks.set_left_track_speed(-60)
        self.assertEqual(self.tracks.get_left_track_speed(), -60)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_rev_speed(60))

    def test_set_left_track_speed_reverse(self):
        self.tracks.left_channel_reverse = True
        self.tracks.set_left_track_speed(40)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_rev_speed(40))
        self.tracks.set_left_track_speed(-40)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_fw_speed(40))

    def test_set_right_track_speed(self):
        self.tracks.right_channel_reverse = False
        self.tracks.set_right_track_speed(70)
        self.assertEqual(self.tracks.get_right_track_speed(), 70)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_fw_speed(70))

        self.tracks.set_right_track_speed(-80)
        self.assertEqual(self.tracks.get_right_track_speed(), -80)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_rev_speed(80))

    def test_set_right_track_speed_reverse(self):
        self.tracks.right_channel_reverse = True
        self.tracks.set_right_track_speed(30)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_rev_speed(30))
        self.tracks.set_right_track_speed(-30)
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_fw_speed(30))

    def test_set_left_track_speed_pwm_exception(self):
        # Simulate hardware failure
        def fail_set_pwm(channel, on, off):
            raise RuntimeError("fail")
        self.tracks.pwm.set_pwm = fail_set_pwm
        with self.assertRaises(TracksError):
            self.tracks.set_left_track_speed(10)

    def test_set_right_track_speed_pwm_exception(self):
        def fail_set_pwm(channel, on, off):
            raise RuntimeError("fail")
        self.tracks.pwm.set_pwm = fail_set_pwm
        with self.assertRaises(TracksError):
            self.tracks.set_right_track_speed(10)

    def test_move_duration_validation(self):
        # Out of bounds negative: logs warning, clamps to 0.01
        with self.assertLogs(level="WARNING") as cm:
            self.assertEqual(self.tracks.sanitize_duration(-1), 0.01)
            self.assertTrue(any("clamping to limits" in msg for msg in cm.output))
        # Out of bounds above max: logs warning, clamps to max
        with self.assertLogs(level="WARNING") as cm:
            self.assertEqual(
                self.tracks.sanitize_duration(self.tracks.move_duration_max + 1),
                self.tracks.move_duration_max
            )
            self.assertTrue(any("clamping to limits" in msg for msg in cm.output))
        # In bounds: no warning, rounds to 2 decimals
        self.assertEqual(self.tracks.sanitize_duration(2.345), 2.35)
        # Conversion error: logs error, raises TracksError
        with self.assertLogs(level="ERROR") as cm:
            with self.assertRaises(TracksError):
                self.tracks.sanitize_duration("notanumber")
            self.assertTrue(any("Could not convert duration value" in msg for msg in cm.output))

    def test_move_and_stop(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        # Patch set_left/right_track_speed to not call hardware
        orig_set_left = self.tracks.set_left_track_speed
        orig_set_right = self.tracks.set_right_track_speed
        self.tracks.set_left_track_speed = lambda x=0: setattr(self.tracks, "_left_track_speed", x)
        self.tracks.set_right_track_speed = lambda x=0: setattr(self.tracks, "_right_track_speed", x)
        self.tracks.stop()
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)
        # Restore originals
        self.tracks.set_left_track_speed = orig_set_left
        self.tracks.set_right_track_speed = orig_set_right
        time.sleep = orig_sleep

    def test_stop_calls_pwm(self):
        # Actually test hardware call path
        self.tracks.set_left_track_speed(50)
        self.tracks.set_right_track_speed(50)
        self.tracks.stop()
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)

    def test_track_width_cm_settable(self):
        self.tracks.track_width_cm = 20.0
        self.assertEqual(self.tracks.track_width_cm, 20.0)

    def test_user_can_change_channels(self):
        self.tracks.left_channel = 5
        self.tracks.right_channel = 6
        self.assertEqual(self.tracks.left_channel, 5)
        self.assertEqual(self.tracks.right_channel, 6)

    def test_sanitize_speed_clamping_and_logging(self):
        # Should clamp and log warning for out-of-bounds
        with self.assertLogs(level="WARNING") as cm:
            self.assertEqual(self.tracks.sanitize_speed(150), 100)
            self.assertTrue(any("clamping to limits" in msg for msg in cm.output))
        with self.assertLogs(level="WARNING") as cm:
            self.assertEqual(self.tracks.sanitize_speed(-150), -100)
            self.assertTrue(any("clamping to limits" in msg for msg in cm.output))

    def test_sanitize_speed_conversion_error(self):
        # Should log error and return 0 for invalid input
        with self.assertLogs(level="ERROR") as cm:
            self.assertEqual(self.tracks.sanitize_speed("notanumber"), 0)
            self.assertTrue(any("Could not convert speed value" in msg for msg in cm.output))

    def test_get_pwm_fw_speed_edges(self):
        # 0, 1, 99, 100
        self.assertEqual(self.tracks.get_pwm_fw_speed(0), self.tracks.pwm_stop)
        self.assertEqual(self.tracks.get_pwm_fw_speed(1), self.tracks.pwm_fw_min - round((1 * 90) / 100))
        self.assertEqual(self.tracks.get_pwm_fw_speed(99), self.tracks.pwm_fw_min - round((99 * 90) / 100))
        self.assertEqual(self.tracks.get_pwm_fw_speed(100), self.tracks.pwm_fw_max)

    def test_get_pwm_rev_speed_edges(self):
        self.assertEqual(self.tracks.get_pwm_rev_speed(0), self.tracks.pwm_stop)
        self.assertEqual(self.tracks.get_pwm_rev_speed(1), self.tracks.pwm_rev_min + round((1 * 90) / 100))
        self.assertEqual(self.tracks.get_pwm_rev_speed(99), self.tracks.pwm_rev_min + round((99 * 90) / 100))
        self.assertEqual(self.tracks.get_pwm_rev_speed(100), self.tracks.pwm_rev_max)

    def test_track_speeds_for_turn(self):
        # Spin in place left
        l, r = self.tracks._track_speeds_for_turn(70, 0, "left")
        self.assertEqual((l, r), (-70, 70))
        # Spin in place right
        l, r = self.tracks._track_speeds_for_turn(70, 0, "right")
        self.assertEqual((l, r), (70, -70))
        # Arc turn left
        l, r = self.tracks._track_speeds_for_turn(70, 20, "left")
        self.assertIsInstance(l, int)
        self.assertIsInstance(r, int)
        # Arc turn right
        l, r = self.tracks._track_speeds_for_turn(70, 20, "right")
        self.assertIsInstance(l, int)
        self.assertIsInstance(r, int)

    def test_turn_duration_for_angle(self):
        """Test _turn_duration_for_angle for correct duration calculation and error handling.

        This test ensures that:
        - Duration is a positive float for normal spins and arcs.
        - Speed and duration clamping log warnings and clamp as expected.
        - Very large/small angles clamp duration to max/min.
        - Zero speed raises TracksError.
        """
        # Normal spin in place (radius 0)
        duration = self.tracks._turn_duration_for_angle(70, 0, 180)
        self.assertIsInstance(duration, float)
        self.assertGreater(duration, 0)

        # Normal arc turn (radius > 0)
        duration = self.tracks._turn_duration_for_angle(70, 20, 90)
        self.assertIsInstance(duration, float)
        self.assertGreater(duration, 0)

        # Speed clamping: input below min
        with self.assertLogs(level="WARNING") as cm:
            duration = self.tracks._turn_duration_for_angle(2, 20, 90)
            self.assertIsInstance(duration, float)
            self.assertTrue(any("clamped" in msg for msg in cm.output))

        # Duration clamping: very large angle triggers max clamp
        with self.assertLogs(level="WARNING") as cm:
            duration = self.tracks._turn_duration_for_angle(100, 20, 99999)
            self.assertLessEqual(duration, self.tracks.move_duration_max)
            self.assertTrue(any("Turn duration" in msg and "clamped" in msg for msg in cm.output))

        # Duration clamping: very small angle triggers min clamp (now 0.1)
        with self.assertLogs(level="WARNING") as cm:
            duration = self.tracks._turn_duration_for_angle(100, 20, 0.0001)
            self.assertAlmostEqual(duration, 0.1, places=6)
            self.assertTrue(any("Turn duration" in msg and "clamped" in msg for msg in cm.output))

        # Zero speed raises TracksError
        with self.assertRaises(TracksError):
            self.tracks._turn_duration_for_angle(0, 20, 90)

    def test_turn_duration_for_angle_with_accel(self):
        # Normal acceleration from 0 to 70, should NOT log a warning (no clamping)
        duration = self.tracks._turn_duration_for_angle_with_accel(
            start_speed=0,
            target_speed=70,
            radius_cm=20,
            angle_deg=90,
            accel=40,
        )
        self.assertIsInstance(duration, float)
        self.assertGreaterEqual(duration, 0)

        # Acceleration from 2 (should clamp to 5) to 120 (should clamp to 100)
        with self.assertLogs(level="WARNING") as cm:
            duration2 = self.tracks._turn_duration_for_angle_with_accel(
                start_speed=2,
                target_speed=120,
                radius_cm=20,
                angle_deg=90,
                accel=40,
            )
            self.assertIsInstance(duration2, float)
            self.assertGreaterEqual(duration2, 0)
            self.assertTrue(any("clamped" in msg for msg in cm.output))

        # Spin in place, duration clamping to max
        with self.assertLogs(level="WARNING") as cm:
            duration3 = self.tracks._turn_duration_for_angle_with_accel(
                start_speed=0,
                target_speed=70,
                radius_cm=0,
                angle_deg=99999,
                accel=40,
            )
            self.assertIsInstance(duration3, float)
            self.assertLessEqual(duration3, self.tracks.move_duration_max)
            self.assertTrue(any("Turn duration" in msg and "clamped" in msg for msg in cm.output))

        # Duration clamping: very small angle triggers min clamp (now 0.1)
        with self.assertLogs(level="WARNING") as cm:
            duration4 = self.tracks._turn_duration_for_angle_with_accel(
                start_speed=70,
                target_speed=70,
                radius_cm=20,
                angle_deg=0.0001,
                accel=40,
            )
            self.assertAlmostEqual(duration4, 0.1, places=6)
            self.assertTrue(any("Turn duration" in msg and "clamped" in msg for msg in cm.output))

        # Zero target speed raises
        with self.assertRaises(TracksError):
            self.tracks._turn_duration_for_angle_with_accel(
                start_speed=0,
                target_speed=0,
                radius_cm=20,
                angle_deg=90,
                accel=40,
            )

        # Zero accel raises
        with self.assertRaises(TracksError):
            self.tracks._turn_duration_for_angle_with_accel(
                start_speed=0,
                target_speed=70,
                radius_cm=20,
                angle_deg=90,
                accel=0,
            )

    def test_turn_and_turn_async_duration_selection(self):
        # Patch move and move_async to capture duration
        durations = {}
        def fake_move(left, right, duration, **kwargs):
            durations['sync'] = duration
        async def fake_move_async(left, right, duration, **kwargs):
            durations['async'] = duration

        self.tracks.move = fake_move
        self.tracks.move_async = fake_move_async

        # Use a large angle to avoid duration clamping for meaningful comparison
        test_angle = 720

        # No accel, angle_deg given (spin in place, high speed)
        self.tracks.get_left_track_speed = lambda: 10
        self.tracks.get_right_track_speed = lambda: 10
        self.tracks.turn(100, 0, "left", angle_deg=test_angle)
        self.assertIn('sync', durations)
        no_accel_duration = durations['sync']

        # With accel, angle_deg given (spin in place, high accel)
        self.tracks.get_left_track_speed = lambda: 20
        self.tracks.get_right_track_speed = lambda: 20
        self.tracks.turn(100, 0, "left", angle_deg=test_angle, accel=200)
        self.assertIn('sync', durations)
        accel_duration = durations['sync']
        self.assertGreater(accel_duration, 0)
        # Durations should differ due to acceleration
        self.assertNotEqual(no_accel_duration, accel_duration)

        # Async version, with accel
        self.tracks.get_left_track_speed = lambda: 30
        self.tracks.get_right_track_speed = lambda: 30
        asyncio.run(self.tracks.turn_async(70, 20, "right", angle_deg=180, accel=40))
        self.assertIn('async', durations)
        self.assertGreater(durations['async'], 0)

        # duration param takes precedence, angle_deg ignored
        durations.clear()
        self.tracks.turn(70, 20, "left", duration=2.5)
        self.assertEqual(durations['sync'], 2.5)

        # Both duration and angle_deg None raises
        with self.assertRaises(TracksError):
            self.tracks.turn(70, 20, "left")

        # Invalid direction raises
        with self.assertRaises(TracksError):
            self.tracks.turn(70, 20, "up", angle_deg=90)

        # Negative radius raises
        with self.assertRaises(TracksError):
            self.tracks.turn(70, -1, "left", angle_deg=90)

        # Async: duration param takes precedence
        durations.clear()
        asyncio.run(self.tracks.turn_async(70, 20, "right", duration=1.5))
        self.assertEqual(durations['async'], 1.5)

        # Async: Both duration and angle_deg None raises
        with self.assertRaises(TracksError):
            asyncio.run(self.tracks.turn_async(70, 20, "left"))

        # Async: Invalid direction raises
        with self.assertRaises(TracksError):
            asyncio.run(self.tracks.turn_async(70, 20, "up", angle_deg=90))

        # Async: Negative radius raises
        with self.assertRaises(TracksError):
            asyncio.run(self.tracks.turn_async(70, -1, "left", angle_deg=90))

 
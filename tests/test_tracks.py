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
        # Should use get_pwm_fw_speed for positive speed
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_fw_speed(50))

        self.tracks.set_left_track_speed(-60)
        self.assertEqual(self.tracks.get_left_track_speed(), -60)
        # Should use get_pwm_rev_speed for negative speed
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_rev_speed(60))

    def test_set_left_track_speed_reverse(self):
        self.tracks.left_channel_reverse = True
        self.tracks.set_left_track_speed(40)
        # For reversed: positive speed uses get_pwm_rev_speed
        self.assertEqual(self.dummy_pwm.calls[-1][2], self.tracks.get_pwm_rev_speed(40))
        self.tracks.set_left_track_speed(-40)
        # For reversed: negative speed uses get_pwm_fw_speed
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

    def test_move_duration_validation(self):
        with self.assertRaises(TracksError):
            self.tracks.sanitize_duration(-1)
        with self.assertRaises(TracksError):
            self.tracks.sanitize_duration(self.tracks.move_duration_max + 1)
        self.assertEqual(self.tracks.sanitize_duration(2.345), 2.35)

    def test_move_and_stop(self):
        orig_sleep = time.sleep
        time.sleep = lambda x: None
        self.tracks.set_left_track_speed = lambda x: setattr(self.tracks, "_left_track_speed", x)
        self.tracks.set_right_track_speed = lambda x: setattr(self.tracks, "_right_track_speed", x)
        self.tracks.stop()
        self.assertEqual(self.tracks.get_left_track_speed(), 0)
        self.assertEqual(self.tracks.get_right_track_speed(), 0)
        time.sleep = orig_sleep

    def test_track_width_cm_settable(self):
        self.tracks.track_width_cm = 20.0
        self.assertEqual(self.tracks.track_width_cm, 20.0)

    def test_user_can_change_channels(self):
        self.tracks.left_channel = 5
        self.tracks.right_channel = 6
        self.assertEqual(self.tracks.left_channel, 5)
        self.assertEqual(self.tracks.right_channel, 6)

if __name__ == "__main__":
    unittest.main()

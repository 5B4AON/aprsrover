import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aprsrover.tracks import Tracks, TracksError

class TestTracks(unittest.TestCase):
    """
    Unit tests for the Tracks class.
    """

    def setUp(self) -> None:
        """Set up a mock PWM controller for each test."""
        self.mock_pwm = MagicMock()
        self.tracks = Tracks(pwm=self.mock_pwm)

    def test_init_success(self):
        self.assertTrue(self.tracks.initialized)

    def test_init_failure(self):
        # Simulate failure in set_pwm_freq
        self.mock_pwm.set_pwm_freq.side_effect = Exception("fail")
        with self.assertRaises(TracksError):
            Tracks(pwm=self.mock_pwm)

    def test_get_pwm_fw_speed(self) -> None:
        """Test PWM value calculation for forward speeds."""
        self.assertEqual(Tracks.get_pwm_fw_speed(0), Tracks.PWM_STOP)
        self.assertEqual(Tracks.get_pwm_fw_speed(100), Tracks.PWM_FW_MAX)
        self.assertEqual(Tracks.get_pwm_fw_speed(50), Tracks.PWM_FW_MIN - round((50 * 90) / 100))

    def test_get_pwm_rev_speed(self) -> None:
        """Test PWM value calculation for reverse speeds."""
        self.assertEqual(Tracks.get_pwm_rev_speed(0), Tracks.PWM_STOP)
        self.assertEqual(Tracks.get_pwm_rev_speed(100), Tracks.PWM_REV_MAX)
        self.assertEqual(Tracks.get_pwm_rev_speed(50), Tracks.PWM_REV_MIN + round((50 * 90) / 100))

    def test_right_track_forward(self) -> None:
        """Test right track forward motion."""
        self.tracks.right_track(60)
        self.mock_pwm.set_pwm.assert_called_with(
            Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_fw_speed(60)
        )

    def test_right_track_reverse(self) -> None:
        """Test right track reverse motion."""
        self.tracks.right_track(-40)
        self.mock_pwm.set_pwm.assert_called_with(
            Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_rev_speed(40)
        )

    def test_left_track_forward(self) -> None:
        """Test left track forward motion."""
        self.tracks.left_track(80)
        self.mock_pwm.set_pwm.assert_called_with(
            Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(80)
        )

    def test_left_track_reverse(self) -> None:
        """Test left track reverse motion."""
        self.tracks.left_track(-30)
        self.mock_pwm.set_pwm.assert_called_with(
            Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_rev_speed(30)
        )

    def test_init_sets_pwm_freq(self) -> None:
        """Test that PWM frequency is set during initialization."""
        pwm = MagicMock()
        t = Tracks(pwm=pwm)
        pwm.set_pwm_freq.assert_called_with(50)
        self.assertTrue(t.initialized)

    def test_speed_below_min(self) -> None:
        """Test speed below -100 is clamped to -100."""
        self.tracks.right_track(-150)
        self.mock_pwm.set_pwm.assert_called_with(
            Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_rev_speed(100)
        )

    def test_speed_above_max(self) -> None:
        """Test speed above 100 is clamped to 100."""
        self.tracks.left_track(150)
        self.mock_pwm.set_pwm.assert_called_with(
            Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(100)
        )

    def test_non_integer_speed(self) -> None:
        """Test float and string speed values are handled correctly."""
        self.tracks.right_track(42.7)
        self.mock_pwm.set_pwm.assert_called_with(
            Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_fw_speed(42)
        )

        self.tracks.left_track("55")
        self.mock_pwm.set_pwm.assert_called_with(
            Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(55)
        )

    def test_invalid_speed_type(self) -> None:
        """Test invalid speed type defaults to stop."""
        self.tracks.right_track(None)
        self.mock_pwm.set_pwm.assert_called_with(
            Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_fw_speed(0)
        )

    def test_sanitize_duration_valid(self):
        self.assertEqual(Tracks.sanitize_duration(1.234), 1.23)
        self.assertEqual(Tracks.sanitize_duration(0.015), 0.01)
        self.assertEqual(Tracks.sanitize_duration(0.016), 0.02)
        self.assertEqual(Tracks.sanitize_duration(10), 10.0)
        self.assertEqual(Tracks.sanitize_duration("2.5"), 2.5)

    def test_sanitize_duration_invalid(self):
        with self.assertRaises(TracksError):
            Tracks.sanitize_duration(0)
        with self.assertRaises(TracksError):
            Tracks.sanitize_duration(-5)
        with self.assertRaises(TracksError):
            Tracks.sanitize_duration("abc")
        with self.assertRaises(TracksError):
            Tracks.sanitize_duration(None)
        with self.assertRaises(TracksError):
            Tracks.sanitize_duration(11)  # Exceeds MOVE_DURATION_MAX

    def test_move_valid(self):
        # Patch time.sleep to avoid actual delay
        import time as _time
        orig_sleep = _time.sleep
        _time.sleep = MagicMock()
        self.tracks.move(50, -50, 0.5)
        self.mock_pwm.set_pwm.assert_any_call(Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(50))
        self.mock_pwm.set_pwm.assert_any_call(Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_rev_speed(50))
        self.mock_pwm.set_pwm.assert_any_call(Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(0))
        self.mock_pwm.set_pwm.assert_any_call(Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_fw_speed(0))
        _time.sleep.assert_called_with(0.5)
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
        _time.sleep = MagicMock()
        self.tracks.move(150, -150, 1)
        self.mock_pwm.set_pwm.assert_any_call(Tracks.LEFT_CHANNEL, 0, Tracks.get_pwm_fw_speed(100))
        self.mock_pwm.set_pwm.assert_any_call(Tracks.RIGHT_CHANNEL, 0, Tracks.get_pwm_rev_speed(100))
        _time.sleep = orig_sleep

    def test_left_track_pwm_error(self):
        self.mock_pwm.set_pwm.side_effect = Exception("fail")
        with self.assertRaises(TracksError):
            self.tracks.left_track(50)
        self.mock_pwm.set_pwm.side_effect = None

    def test_right_track_pwm_error(self):
        self.mock_pwm.set_pwm.side_effect = Exception("fail")
        with self.assertRaises(TracksError):
            self.tracks.right_track(50)
        self.mock_pwm.set_pwm.side_effect = None

    def test_move_tracks_error(self):
        # Simulate error in left_track
        orig_left_track = self.tracks.left_track
        self.tracks.left_track = lambda speed=0: (_ for _ in ()).throw(Exception("fail"))
        with self.assertRaises(TracksError):
            self.tracks.move(10, 10, 0.1)
        self.tracks.left_track = orig_left_track

if __name__ == "__main__":
    unittest.main()

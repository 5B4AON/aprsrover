"""
tracks.py - Rover track control utilities using PWM

This module provides the Tracks class for controlling left and right rover tracks
using a PWM controller (such as Adafruit PCA9685). It includes:

- Methods to set speed and direction for each track independently
- Method to move both tracks simultaneously for a specified duration
- Utility functions to convert speed values to PWM signals
- Input validation for speed and duration
- Designed for use with Adafruit PCA9685 PWM driver

Usage example:

    from aprsrover.tracks import Tracks

    tracks = Tracks()
    tracks.left_track(50)      # Start moving left track forward at 50% speed
    tracks.left_track(0)       # Stop left track
    tracks.right_track(-30)    # Start moving right track reverse at 30% speed
    tracks.right_track(0)      # Stop right track
    tracks.move(60, -60, 2.5)  # Move both tracks for 2.5 seconds

See the README.md for more usage examples and parameter details.

Dependencies:
    - Adafruit-PCA9685

This module is designed to be imported and used from other Python scripts.
"""

import Adafruit_PCA9685
import logging
import time
from typing import Optional, Union

__all__ = ["Tracks", "TracksError"]


class TracksError(Exception):
    """Custom exception for Tracks-related errors."""
    pass


class Tracks:
    """
    Controls the left and right tracks of a rover using a PWM controller.
    """

    PWM_FW_MIN: int = 307
    PWM_FW_MAX: int = 217
    PWM_STOP: int = 318
    PWM_REV_MIN: int = 329
    PWM_REV_MAX: int = 419
    LEFT_CHANNEL: int = 8
    RIGHT_CHANNEL: int = 9
    MOVE_DURATION_MAX: int = 10  # Maximum allowed duration in seconds

    def __init__(self, pwm: Optional[Adafruit_PCA9685.PCA9685] = None) -> None:
        """
        Initialize the Tracks controller.

        Args:
            pwm: Optional PWM controller instance for dependency injection/testing.

        Raises:
            TracksError: If the PWM controller fails to initialize.
        """
        self.pwm = pwm or Adafruit_PCA9685.PCA9685()
        self.initialized = False
        self.init()

    def init(self) -> None:
        """
        Initialize the PWM controller and set frequency.

        Raises:
            TracksError: If the PWM controller fails to initialize.
        """
        try:
            self.pwm.set_pwm_freq(50)
            self.initialized = True
        except Exception as e:
            self.initialized = False
            logging.error("Failed to initialize PWM controller: %s", e)
            raise TracksError(f"Failed to initialize PWM controller: {e}")

    @staticmethod
    def _sanitize_speed(speed: Union[int, float, str]) -> int:
        """
        Convert speed to int and clamp to [-100, 100].

        Args:
            speed: The speed value to sanitize.

        Returns:
            int: Sanitized speed value.
        """
        try:
            x = int(float(speed))
        except (ValueError, TypeError):
            x = 0
        return max(-100, min(100, x))

    @staticmethod
    def get_pwm_fw_speed(speed: Union[int, float, str] = 0) -> int:
        """
        Calculate the PWM value for forward speed.

        Args:
            speed: Speed value (0-100), where 0 is stop and 100 is maximum forward.

        Returns:
            int: PWM value for forward motion.
        """
        x = Tracks._sanitize_speed(speed)
        x = max(0, min(100, x))  # Only allow 0-100 for forward
        if x > 99:
            return Tracks.PWM_FW_MAX
        elif x < 1:
            return Tracks.PWM_STOP
        else:
            return Tracks.PWM_FW_MIN - round((x * 90) / 100)

    @staticmethod
    def get_pwm_rev_speed(speed: Union[int, float, str] = 0) -> int:
        """
        Calculate the PWM value for reverse speed.

        Args:
            speed: Speed value (0-100), where 0 is stop and 100 is maximum reverse.

        Returns:
            int: PWM value for reverse motion.
        """
        x = Tracks._sanitize_speed(speed)
        x = max(0, min(100, x))  # Only allow 0-100 for reverse
        if x > 99:
            return Tracks.PWM_REV_MAX
        elif x < 1:
            return Tracks.PWM_STOP
        else:
            return Tracks.PWM_REV_MIN + round((x * 90) / 100)

    def right_track(self, speed: Union[int, float, str] = 0) -> None:
        """
        Set the speed and direction of the right track.

        Args:
            speed: Speed value (-100 to 100). Negative for reverse, positive for forward, 0 for stop.
        """
        x = self._sanitize_speed(speed)
        try:
            if x < 0:
                self.pwm.set_pwm(self.RIGHT_CHANNEL, 0, self.get_pwm_rev_speed(-x))
            else:
                self.pwm.set_pwm(self.RIGHT_CHANNEL, 0, self.get_pwm_fw_speed(x))
        except Exception as e:
            logging.error("Failed to set right track PWM: %s", e)
            raise TracksError(f"Failed to set right track PWM: {e}")

    def left_track(self, speed: Union[int, float, str] = 0) -> None:
        """
        Set the speed and direction of the left track.

        Args:
            speed: Speed value (-100 to 100). Negative for reverse, positive for forward, 0 for stop.
        """
        x = self._sanitize_speed(speed)
        try:
            if x < 0:
                self.pwm.set_pwm(self.LEFT_CHANNEL, 0, self.get_pwm_rev_speed(-x))
            else:
                self.pwm.set_pwm(self.LEFT_CHANNEL, 0, self.get_pwm_fw_speed(x))
        except Exception as e:
            logging.error("Failed to set left track PWM: %s", e)
            raise TracksError(f"Failed to set left track PWM: {e}")

    @staticmethod
    def sanitize_duration(duration: float) -> float:
        """
        Validate and sanitize the duration value.

        Args:
            duration: The duration in seconds.

        Returns:
            float: Duration clamped to a minimum of 0.01 and rounded to 2 decimal places.

        Raises:
            TracksError: If duration is not a positive number or exceeds MOVE_DURATION_MAX.
        """
        try:
            d = float(duration)
        except (ValueError, TypeError):
            logging.error("Duration must be a positive float. Got: %r", duration)
            raise TracksError("Duration must be a positive float.")
        if d <= 0:
            logging.error("Duration must be a positive float. Got: %r", duration)
            raise TracksError("Duration must be a positive float.")
        if d > Tracks.MOVE_DURATION_MAX:
            logging.error(
                "Duration %.2f exceeds MOVE_DURATION_MAX (%d seconds).", d, Tracks.MOVE_DURATION_MAX
            )
            raise TracksError(f"Duration must not exceed {Tracks.MOVE_DURATION_MAX} seconds.")
        return round(max(d, 0.01), 2)

    def move(
        self,
        left_speed: Union[int, float, str],
        right_speed: Union[int, float, str],
        duration: float,
    ) -> None:
        """
        Move both tracks at specified speeds for a given duration.

        Args:
            left_speed: Speed for the left track (-100 to 100).
            right_speed: Speed for the right track (-100 to 100).
            duration: Duration in seconds (positive float, max 2 decimal places, <= MOVE_DURATION_MAX).

        Raises:
            TracksError: If duration is not a positive float or exceeds MOVE_DURATION_MAX.
        """
        left = self._sanitize_speed(left_speed)
        right = self._sanitize_speed(right_speed)
        dur = self.sanitize_duration(duration)
        try:
            self.left_track(left)
            self.right_track(right)
            time.sleep(dur)
            self.left_track(0)
            self.right_track(0)
        except Exception as e:
            logging.error("Failed to move tracks: %s", e)
            raise TracksError(f"Failed to move tracks: {e}")

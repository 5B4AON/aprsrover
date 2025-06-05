"""
tracks.py - Rover track control utilities using PWM

This module provides the Tracks class for controlling left and right rover tracks
using a PWM controller (such as Adafruit PCA9685).

Features:

- Methods to set speed and direction for each track independently:
    - `set_left_track_speed()`, `set_right_track_speed()`
    - Query current speed with `get_left_track_speed()`, `get_right_track_speed()`
- Methods to move both tracks simultaneously for a specified duration:
    - Synchronous: `move()` (supports optional acceleration smoothing)
    - Asynchronous: `move_async()` (supports optional acceleration smoothing and interruption)
- Methods to turn the rover along an arc or in place, specifying speed, turning radius, and direction:
    - Synchronous: `turn()` (supports optional acceleration smoothing)
    - Asynchronous: `turn_async()` (supports optional acceleration smoothing and interruption)
    - Specify either duration (in seconds) or angle (in degrees) for the turn
    - Automatically computes correct speed for each track based on radius and direction
- Utility functions to convert speed values to PWM signals
- Input validation for speed, duration, acceleration, interval, radius, and direction parameters
- Designed for use with Adafruit PCA9685 PWM driver or a custom/mock PWM controller for testing
- All hardware access is abstracted for easy mocking in tests
- Custom exception: `TracksError` for granular error handling

Usage example:

    from aprsrover.tracks import Tracks
    import asyncio

    tracks = Tracks()
    tracks.set_left_track_speed(50)      # Start moving left track forward at 50% speed
    tracks.set_left_track_speed(0)       # Stop left track
    tracks.set_right_track_speed(-30)    # Start moving right track reverse at 30% speed
    tracks.set_right_track_speed(0)      # Stop right track
    tracks.move(60, -60, 2.5)            # Move both tracks for 2.5 seconds

    # Synchronous movement with acceleration smoothing (ramps to speed over 1s, holds, then stops)
    tracks.move(80, 80, 5, accel=80, accel_interval=0.1)

    # Synchronous turn: spin in place 180 degrees left
    tracks.turn(70, 0, 'left', angle_deg=180)

    # Synchronous arc turn: arc right for 2.5 seconds
    tracks.turn(60, 20, 'right', duration=2.5)

    # Synchronous arc turn with acceleration smoothing
    tracks.turn(50, 30, 'left', angle_deg=90, accel=40, accel_interval=0.1)

    # Asynchronous movement with interruption, speed query, and acceleration smoothing:
    async def main():
        tracks = Tracks()
        move_task = asyncio.create_task(tracks.move_async(80, 80, 10, accel=40))
        await asyncio.sleep(2)  # Simulate obstacle detection after 2 seconds
        move_task.cancel()      # Interrupt movement (tracks will keep running at last speed)
        try:
            await move_task
        except asyncio.CancelledError:
            print("Move interrupted!")
            # Query current speeds
            left = tracks.get_left_track_speed()
            right = tracks.get_right_track_speed()
            print(f"Current speeds: left={left}, right={right}")
            # Stop the rover
            tracks.set_left_track_speed(0)
            tracks.set_right_track_speed(0)
            print("Tracks stopped.")

        # Asynchronous turn: spin in place 90 degrees left
        await tracks.turn_async(70, 0, 'left', angle_deg=90)

        # Asynchronous arc turn with acceleration smoothing
        await tracks.turn_async(40, 30, 'left', angle_deg=45, accel=30, accel_interval=0.05)

See the README.md for more usage examples and parameter details.

Dependencies:
    - Adafruit-PCA9685

This module is designed to be imported and used from other Python scripts.

"""

import asyncio
import logging
import math
import time
from typing import Optional, Union, Protocol

__all__ = ["Tracks", "TracksError", "PWMControllerInterface"]


class TracksError(Exception):
    """Custom exception for Tracks-related errors."""
    pass


class PWMControllerInterface(Protocol):
    """
    Protocol for PWM controller to allow dependency injection and testing.

    Methods:
        set_pwm(channel: int, on: int, off: int): Set PWM value for a channel.
    """
    def set_pwm(self, channel: int, on: int, off: int) -> None:
        ...


class Tracks:
    """
    Controls the left and right tracks of a rover using a PWM controller.

    Provides synchronous and asynchronous methods to set track speeds, move for a duration,
    and perform turns (in place or along an arc) with optional acceleration smoothing.

    All hardware access is abstracted for easy mocking in tests.
    """

    PWM_FW_MIN: int = 307
    PWM_FW_MAX: int = 217
    PWM_STOP: int = 318
    PWM_REV_MIN: int = 329
    PWM_REV_MAX: int = 419
    LEFT_CHANNEL: int = 8
    RIGHT_CHANNEL: int = 9
    MOVE_DURATION_MAX: int = 10  # Maximum allowed duration in seconds
    track_width_cm: float = 15.0  # Distance between tracks in cm (adjust as needed)

    def __init__(self, pwm: Optional[PWMControllerInterface] = None) -> None:
        """
        Initialize the Tracks controller.

        Args:
            pwm: Optional PWM controller instance for dependency injection/testing.

        Raises:
            TracksError: If the PWM controller fails to initialize.
        """
        if pwm is not None:
            self.pwm = pwm
        else:
            try:
                import Adafruit_PCA9685
                self.pwm = Adafruit_PCA9685.PCA9685()
            except ImportError as e:
                raise TracksError("Adafruit_PCA9685 not available and no PWM controller provided.") from e
        self.initialized = False
        self.init()

    def init(self) -> None:
        """
        Initialize the PWM controller and set frequency.

        Raises:
            TracksError: If the PWM controller fails to initialize.
        """
        try:
            if hasattr(self.pwm, "set_pwm_freq"):
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
            int: Sanitized speed value in range [-100, 100].
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

    def get_left_track_speed(self) -> int:
        """
        Get the current speed setting for the left track.

        Returns:
            int: The last commanded speed for the left track (-100 to 100).
        """
        return getattr(self, "_left_track_speed", 0)

    def get_right_track_speed(self) -> int:
        """
        Get the current speed setting for the right track.

        Returns:
            int: The last commanded speed for the right track (-100 to 100).
        """
        return getattr(self, "_right_track_speed", 0)

    def set_left_track_speed(self, left_track_speed: Union[int, float, str] = 0) -> None:
        """
        Set the speed and direction of the left track.

        Args:
            left_track_speed: Speed value (-100 to 100). Negative for reverse, positive for forward, 0 for stop.

        Raises:
            TracksError: If setting the PWM value fails.
        """
        x = self._sanitize_speed(left_track_speed)
        self._left_track_speed = x  # Track the last commanded speed
        try:
            if x < 0:
                self.pwm.set_pwm(self.LEFT_CHANNEL, 0, self.get_pwm_rev_speed(-x))
            else:
                self.pwm.set_pwm(self.LEFT_CHANNEL, 0, self.get_pwm_fw_speed(x))
        except Exception as e:
            logging.error("Failed to set left track PWM: %s", e)
            raise TracksError(f"Failed to set left track PWM: {e}")

    def set_right_track_speed(self, right_track_speed: Union[int, float, str] = 0) -> None:
        """
        Set the speed and direction of the right track.

        Args:
            right_track_speed: Speed value (-100 to 100). Negative for reverse, positive for forward, 0 for stop.

        Raises:
            TracksError: If setting the PWM value fails.
        """
        x = self._sanitize_speed(right_track_speed)
        self._right_track_speed = x  # Track the last commanded speed
        try:
            if x < 0:
                self.pwm.set_pwm(self.RIGHT_CHANNEL, 0, self.get_pwm_rev_speed(-x))
            else:
                self.pwm.set_pwm(self.RIGHT_CHANNEL, 0, self.get_pwm_fw_speed(x))
        except Exception as e:
            logging.error("Failed to set right track PWM: %s", e)
            raise TracksError(f"Failed to set right track PWM: {e}")

    def sanitize_duration(self, duration: float) -> float:
        """
        Validate and clamp the duration for movement.

        Args:
            duration: Duration in seconds.

        Returns:
            float: Validated duration.

        Raises:
            TracksError: If duration is not a positive float or exceeds MOVE_DURATION_MAX.
        """
        try:
            d = float(duration)
        except (ValueError, TypeError):
            raise TracksError("Duration must be a number.")
        if not (0 < d <= self.MOVE_DURATION_MAX):
            raise TracksError(f"Duration must be >0 and <= {self.MOVE_DURATION_MAX} seconds.")
        return round(d, 2)

    def move(
        self,
        left_track_speed: Union[int, float, str],
        right_track_speed: Union[int, float, str],
        duration: float,
        accel: Optional[float] = None,
        accel_interval: float = 0.05,
    ) -> None:
        """
        Move both tracks at specified speeds for a given duration, with optional acceleration smoothing.

        If `accel` is provided and > 0, the speed ramps smoothly from the current speed to the target speed
        over the specified duration, using the given acceleration rate and interval. If `accel` is None or <= 0,
        the speed jumps instantly to the target value.

        Args:
            left_track_speed: Speed for the left track (-100 to 100).
            right_track_speed: Speed for the right track (-100 to 100).
            duration: Duration in seconds (positive float, max 2 decimal places, <= MOVE_DURATION_MAX).
            accel: Optional acceleration in percent per second (e.g., 100 for full speed in 1s).
                   If None or <= 0, jumps instantly to target speed.
            accel_interval: Time step for acceleration smoothing in seconds.

        Raises:
            TracksError: If duration or acceleration parameters are invalid.
        """
        left_target = self._sanitize_speed(left_track_speed)
        right_target = self._sanitize_speed(right_track_speed)
        dur = self.sanitize_duration(duration)

        # Validate accel and accel_interval
        if accel is not None:
            try:
                accel_val = float(accel)
            except (ValueError, TypeError):
                raise TracksError("Acceleration (accel) must be a number or None.")
            if accel_val < 0 or accel_val > 1000:
                raise TracksError("Acceleration (accel) must be between 0 and 1000 percent per second.")
        else:
            accel_val = None

        try:
            accel_interval_val = float(accel_interval)
        except (ValueError, TypeError):
            raise TracksError("Acceleration interval (accel_interval) must be a positive float.")
        if accel_interval_val <= 0 or accel_interval_val > dur:
            raise TracksError("Acceleration interval (accel_interval) must be > 0 and <= duration.")

        # Use current speeds as starting point for ramping
        left_start = self.get_left_track_speed()
        right_start = self.get_right_track_speed()

        try:
            if accel_val is None or accel_val <= 0:
                # No smoothing, jump to target
                logging.debug(f"Jumping to target speeds: left={left_target}, right={right_target}, for={dur:03.2f} seconds")
                self.set_left_track_speed(left_target)
                self.set_right_track_speed(right_target)
                time.sleep(dur)
            else:
                # Smooth acceleration from current speed to target speed
                logging.debug(f"Smoothly accelerating to target speeds: left={left_target}, right={right_target}, for={dur:03.2f} seconds with accel={accel_val}%")
                import math
                left_delta = left_target - left_start
                right_delta = right_target - right_start
                steps_left = (
                    math.ceil(abs(left_delta) / (accel_val * accel_interval_val))
                    if accel_val > 0 and left_delta != 0 else 1
                )
                steps_right = (
                    math.ceil(abs(right_delta) / (accel_val * accel_interval_val))
                    if accel_val > 0 and right_delta != 0 else 1
                )
                steps = max(1, int(max(steps_left, steps_right)))
                total_steps = max(1, int(dur / accel_interval_val))
                steps = min(steps, total_steps)
                for i in range(steps):
                    frac = (i + 1) / steps
                    left = round(left_start + (left_target - left_start) * frac)
                    right = round(right_start + (right_target - right_start) * frac)
                    self.set_left_track_speed(left)
                    self.set_right_track_speed(right)
                    time.sleep(accel_interval_val)
                # Hold at target for the remainder
                remaining = dur - steps * accel_interval_val
                if remaining > 0:
                    self.set_left_track_speed(left_target)
                    self.set_right_track_speed(right_target)
                    time.sleep(remaining)
            self.set_left_track_speed(0)
            self.set_right_track_speed(0)
        except Exception as e:
            self.set_left_track_speed(0)
            self.set_right_track_speed(0)
            logging.error("Failed to move tracks: %s", e)
            raise TracksError(f"Failed to move tracks: {e}")

    async def move_async(
        self,
        left_track_speed: Union[int, float, str],
        right_track_speed: Union[int, float, str],
        duration: float,
        accel: Optional[float] = None,
        accel_interval: float = 0.05,
    ) -> None:
        """
        Asynchronously move both tracks at specified speeds for a given duration,
        with optional acceleration smoothing.

        If `accel` is provided and > 0, the speed ramps smoothly from the current speed to the target speed
        over the specified duration, using the given acceleration rate and interval. If `accel` is None or <= 0,
        the speed jumps instantly to the target value.

        This method can be cancelled (e.g., via asyncio.Task.cancel()), but will only stop the tracks
        if the duration completes or an exception occurs. If cancelled, the tracks will continue
        running at the last set speed.

        Args:
            left_track_speed: Target speed for the left track (-100 to 100).
            right_track_speed: Target speed for the right track (-100 to 100).
            duration: Duration in seconds (positive float, <= MOVE_DURATION_MAX).
            accel: Optional acceleration in percent per second (e.g., 100 for full speed in 1s).
                   If None, jumps instantly to target speed.
            accel_interval: Time step for acceleration smoothing in seconds.

        Raises:
            TracksError: If duration or acceleration parameters are invalid.
            asyncio.CancelledError: If the move is interrupted (tracks will NOT be stopped).

        Example:
            await tracks.move_async(80, 80, 5, accel=40)  # Smoothly ramp to 80 over 2s, hold, then stop
        """
        left_target = self._sanitize_speed(left_track_speed)
        right_target = self._sanitize_speed(right_track_speed)
        dur = self.sanitize_duration(duration)

        # Validate accel and accel_interval
        if accel is not None:
            try:
                accel_val = float(accel)
            except (ValueError, TypeError):
                raise TracksError("Acceleration (accel) must be a number or None.")
            if accel_val < 0 or accel_val > 1000:
                raise TracksError("Acceleration (accel) must be between 0 and 1000 percent per second.")
        else:
            accel_val = None

        try:
            accel_interval_val = float(accel_interval)
        except (ValueError, TypeError):
            raise TracksError("Acceleration interval (accel_interval) must be a positive float.")
        if accel_interval_val <= 0 or accel_interval_val > dur:
            raise TracksError("Acceleration interval (accel_interval) must be > 0 and <= duration.")

        # Use current speeds as starting point for ramping
        left_start = self.get_left_track_speed()
        right_start = self.get_right_track_speed()

        try:
            if accel_val is None or accel_val <= 0:
                # No smoothing, jump to target
                logging.debug(f"Jumping to target speeds: left={left_target}, right={right_target}, for={dur:03.2f} seconds")
                self.set_left_track_speed(left_target)
                self.set_right_track_speed(right_target)
                await asyncio.sleep(dur)
            else:
                # Smooth acceleration from current speed to target speed
                logging.debug(f"Smoothly accelerating to target speeds: left={left_target}, right={right_target}, for={dur:03.2f} seconds with accel={accel_val}%")
                import math
                left_delta = left_target - left_start
                right_delta = right_target - right_start
                steps_left = (
                    math.ceil(abs(left_delta) / (accel_val * accel_interval_val))
                    if accel_val > 0 and left_delta != 0 else 1
                )
                steps_right = (
                    math.ceil(abs(right_delta) / (accel_val * accel_interval_val))
                    if accel_val > 0 and right_delta != 0 else 1
                )
                steps = max(1, int(max(steps_left, steps_right)))
                total_steps = max(1, int(dur / accel_interval_val))
                steps = min(steps, total_steps)
                for i in range(steps):
                    frac = (i + 1) / steps
                    left = round(left_start + (left_target - left_start) * frac)
                    right = round(right_start + (right_target - right_start) * frac)
                    self.set_left_track_speed(left)
                    self.set_right_track_speed(right)
                    await asyncio.sleep(accel_interval_val)
                # Hold at target for the remainder
                remaining = dur - steps * accel_interval_val
                if remaining > 0:
                    self.set_left_track_speed(left_target)
                    self.set_right_track_speed(right_target)
                    await asyncio.sleep(remaining)
        except Exception as e:
            self.set_left_track_speed(0)
            self.set_right_track_speed(0)
            raise TracksError(f"Failed to move tracks: {e}")
        else:
            self.set_left_track_speed(0)
            self.set_right_track_speed(0)

    def turn(
        self,
        speed: Union[int, float, str],
        radius_cm: float,
        direction: str,
        duration: Optional[float] = None,
        angle_deg: Optional[float] = None,
        accel: Optional[float] = None,
        accel_interval: float = 0.05,
    ) -> None:
        """
        Turn the rover along an arc or in place, specifying speed, turning radius, and direction.
        Either duration or angle_deg must be provided to define the turn.

        The method computes the correct speed for each track based on the specified radius and direction,
        using differential drive kinematics. If angle_deg is specified, the duration is calculated using
        the calibration: at speed 70, 3.5 seconds moves the rover 30 cm forward.

        Args:
            speed: Overall speed (-100 to 100, positive = forward, negative = reverse).
            radius_cm: Turning radius in centimeters (0 = spin in place, >0 = arc turn).
            direction: 'left' or 'right'.
            duration: Duration of the turn in seconds. Required if angle_deg is not given.
            angle_deg: Angle to turn in degrees (e.g., 180 for half-turn). Required if duration is not given.
            accel: Optional acceleration for smoothing (percent per second).
            accel_interval: Acceleration interval in seconds.

        Raises:
            TracksError: On invalid parameters.

        Example:
            tracks.turn(70, 0, 'left', angle_deg=180)  # Spin in place 180 degrees left
            tracks.turn(60, 20, 'right', duration=2.5) # Arc right for 2.5 seconds
        """
        if direction not in ("left", "right"):
            raise TracksError("Direction must be 'left' or 'right'.")
        speed_val = self._sanitize_speed(speed)
        if speed_val == 0:
            raise TracksError("Speed must be non-zero for turning.")
        if radius_cm < 0:
            raise TracksError("Radius must be >= 0.")

        # Calculate duration if angle_deg is given
        if angle_deg is not None:
            if duration is not None:
                raise TracksError("Specify only one of duration or angle_deg.")
            duration = self._turn_duration_for_angle(
                abs(speed_val), radius_cm, abs(angle_deg)
            )
        if duration is None:
            raise TracksError("Must specify either duration or angle_deg.")

        # Compute track speeds
        left_speed, right_speed = self._track_speeds_for_turn(
            speed_val, radius_cm, direction
        )
        self.move(left_speed, right_speed, duration, accel=accel, accel_interval=accel_interval)

    async def turn_async(
        self,
        speed: Union[int, float, str],
        radius_cm: float,
        direction: str,
        duration: Optional[float] = None,
        angle_deg: Optional[float] = None,
        accel: Optional[float] = None,
        accel_interval: float = 0.05,
    ) -> None:
        """
        Asynchronously turn the rover along an arc or in place, specifying speed, turning radius, and direction.
        Either duration or angle_deg must be provided to define the turn.

        The method computes the correct speed for each track based on the specified radius and direction,
        using differential drive kinematics. If angle_deg is specified, the duration is calculated using
        the calibration: at speed 70, 3.5 seconds moves the rover 30 cm forward.

        Args:
            speed: Overall speed (-100 to 100, positive = forward, negative = reverse).
            radius_cm: Turning radius in centimeters (0 = spin in place, >0 = arc turn).
            direction: 'left' or 'right'.
            duration: Duration of the turn in seconds. Required if angle_deg is not given.
            angle_deg: Angle to turn in degrees (e.g., 180 for half-turn). Required if duration is not given.
            accel: Optional acceleration for smoothing (percent per second).
            accel_interval: Acceleration interval in seconds.

        Raises:
            TracksError: On invalid parameters.

        Example:
            await tracks.turn_async(70, 0, 'left', angle_deg=90)
            await tracks.turn_async(60, 20, 'right', duration=2.5)
        """
        if direction not in ("left", "right"):
            raise TracksError("Direction must be 'left' or 'right'.")
        speed_val = self._sanitize_speed(speed)
        if speed_val == 0:
            raise TracksError("Speed must be non-zero for turning.")
        if radius_cm < 0:
            raise TracksError("Radius must be >= 0.")

        # Calculate duration if angle_deg is given
        if angle_deg is not None:
            if duration is not None:
                raise TracksError("Specify only one of duration or angle_deg.")
            duration = self._turn_duration_for_angle(
                abs(speed_val), radius_cm, abs(angle_deg)
            )
        if duration is None:
            raise TracksError("Must specify either duration or angle_deg.")

        # Compute track speeds
        left_speed, right_speed = self._track_speeds_for_turn(
            speed_val, radius_cm, direction
        )
        await self.move_async(left_speed, right_speed, duration, accel=accel, accel_interval=accel_interval)

    def _track_speeds_for_turn(
        self, speed: int, radius_cm: float, direction: str
    ) -> tuple[int, int]:
        """
        Compute left/right track speeds for a given turn.

        For spin-in-place (radius_cm == 0), one track moves forward and the other in reverse.
        For arc turns, uses differential drive kinematics to compute the correct speeds.

        Args:
            speed: Overall speed (-100 to 100).
            radius_cm: Turning radius in cm (0 = spin in place).
            direction: 'left' or 'right'.

        Returns:
            (left_speed, right_speed): Tuple of speeds for each track.
        """
        w = self.track_width_cm
        if radius_cm == 0:
            # Spin in place: one track forward, one reverse
            if direction == "left":
                return -speed, speed
            else:
                return speed, -speed
        # Arc turn: use differential drive kinematics
        v = speed
        r = radius_cm
        v_l = v * (r - w / 2) / r
        v_r = v * (r + w / 2) / r
        if direction == "left":
            return int(round(v_l)), int(round(v_r))
        else:
            return int(round(v_r)), int(round(v_l))

    def _turn_duration_for_angle(
        self, speed: int, radius_cm: float, angle_deg: float
    ) -> float:
        """
        Calculate duration needed to turn a given angle at a given speed/radius.

        Uses calibration: at speed 70, 3.5 seconds moves the rover 30 cm forward.

        Args:
            speed: Absolute speed (1-100).
            radius_cm: Turning radius in cm (0 = spin in place).
            angle_deg: Angle to turn in degrees.

        Returns:
            Duration in seconds.

        Raises:
            TracksError: If speed is zero.
        """
        if speed == 0:
            raise TracksError("Speed must be non-zero for turn duration calculation.")
        # Calibration: at speed 70, 3.5s -> 30cm straight
        # So: speed 70 = 30cm/3.5s = 8.571 cm/s
        base_speed = 70
        base_cm_per_sec = 30 / 3.5
        cm_per_sec = abs(speed) * (base_cm_per_sec / base_speed)
        if radius_cm == 0:
            # Spin in place: arc length = (track_width_cm * pi) * (angle/360)
            arc_len = self.track_width_cm * math.pi * (angle_deg / 360)
            # Each track travels arc_len in opposite directions
            duration = arc_len / cm_per_sec
        else:
            # Arc turn: arc length = 2*pi*r * (angle/360)
            arc_len = 2 * math.pi * radius_cm * (angle_deg / 360)
            duration = arc_len / cm_per_sec
        return duration

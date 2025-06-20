"""
tracks.py - Rover track control utilities using PWM

This module provides the Tracks class for controlling left and right rover tracks
using a PWM controller (such as Adafruit PCA9685).

Features:

- Methods to set speed and direction for each track independently:
    - `set_left_track_speed()`, `set_right_track_speed()`
    - Query current speed with `get_left_track_speed()`, `get_right_track_speed()`
- Methods to move both tracks simultaneously for a specified duration or distance:
    - Synchronous: `move()` (supports optional acceleration smoothing and optional stop at end)
    - Asynchronous: `move_async()` (supports optional acceleration smoothing, interruption, and optional stop at end)
    - You may specify either a duration (in seconds) or a distance (in centimeters) for the move.
    - If a distance is specified, the duration is automatically calculated using calibration parameters and the current/target speeds.
- Methods to turn the rover along an arc or in place, specifying speed, turning radius, and direction:
    - Synchronous: `turn()` (supports optional acceleration smoothing and optional stop at end)
    - Asynchronous: `turn_async()` (supports optional acceleration smoothing, interruption, and optional stop at end)
    - Specify either duration (in seconds) or angle (in degrees) for the turn
    - Automatically computes correct speed for each track based on radius and direction
- Utility functions to convert speed values to PWM signals
- Input validation for speed, duration, acceleration, interval, radius, and direction parameters
- Designed for use with Adafruit PCA9685 PWM driver or a custom/mock PWM controller for testing
- All hardware access is abstracted for easy mocking in tests
- Custom exception: `TracksError` for granular error handling

Default Parameters and Customization:

The Tracks class exposes several default parameters as class-level constants (prefixed with `DEFAULT_`), such as PWM ranges, channel numbers, and track geometry. When you instantiate a `Tracks` object, these defaults are copied to instance attributes, which you can modify at runtime to suit your hardware setup.

**Default parameters:**
- `DEFAULT_PWM_FW_MIN`: Minimum PWM value for forward motion (default: 307)
- `DEFAULT_PWM_FW_MAX`: Maximum PWM value for forward motion (default: 217)
- `DEFAULT_PWM_STOP`: PWM value for stop (default: 318)
- `DEFAULT_PWM_REV_MIN`: Minimum PWM value for reverse motion (default: 329)
- `DEFAULT_PWM_REV_MAX`: Maximum PWM value for reverse motion (default: 419)
- `DEFAULT_LEFT_CHANNEL`: PWM channel for the left track (default: 8)
- `DEFAULT_LEFT_CHANNEL_REVERSE`: Whether to reverse the left track direction (default: False)
- `DEFAULT_RIGHT_CHANNEL`: PWM channel for the right track (default: 9)
- `DEFAULT_RIGHT_CHANNEL_REVERSE`: Whether to reverse the right track direction (default: True)
- `DEFAULT_MOVE_DURATION_MAX`: Maximum allowed move duration in seconds (default: 10)
- `DEFAULT_TRACK_WIDTH_CM`: Distance between tracks in centimeters (default: 19.0)
- `DEFAULT_BASE_SPEED`: Calibration base speed as a percentage (default: 70)
- `DEFAULT_BASE_DISTANCE`: Calibration base distance in centimeters (default: 30.0)
- `DEFAULT_BASE_DURATION`: Calibration base duration in seconds (default: 3.5)

**Changing parameters at runtime:**
You can modify any of these parameters on a `Tracks` instance after construction. For example:

    from aprsrover.tracks import Tracks

    tracks = Tracks()
    tracks.left_channel_reverse = True  # Reverse left track direction
    tracks.right_channel = 10           # Use channel 10 for right track
    tracks.track_width_cm = 18.5        # Set track width to 18.5 cm
    tracks.base_speed = 75              # Change calibration base speed
    tracks.base_distance = 32.0         # Change calibration base distance
    tracks.base_duration = 3.2          # Change calibration base duration

This allows you to adapt the library to your specific hardware without subclassing or modifying the source.

Requires:

- Python 3.10+
- Adafruit-PCA9685

Usage example:

    from aprsrover.tracks import Tracks
    import asyncio

    tracks = Tracks()
    tracks.set_left_track_speed(50)      # Start moving left track forward at 50% speed
    tracks.set_left_track_speed(0)       # Stop left track
    tracks.set_right_track_speed(-30)    # Start moving right track reverse at 30% speed
    tracks.set_right_track_speed(0)      # Stop right track
    tracks.move(60, -60, duration=2.5)   # Move both tracks for 2.5 seconds (stops at end by default)
    tracks.move(80, 80, distance_cm=100) # Move both tracks for 100 cm (duration auto-calculated)

    # Synchronous movement with acceleration smoothing (ramps to speed over 1s, holds, then stops)
    tracks.move(80, 80, duration=5, accel=80, accel_interval=0.1)

    # Synchronous movement, but do not stop at end (leave tracks running)
    tracks.move(80, 80, duration=5, stop_at_end=False)

    # Synchronous turn: spin in place 180 degrees left
    tracks.turn(70, 0, 'left', angle_deg=180)

    # Synchronous arc turn: arc right for 2.5 seconds
    tracks.turn(60, 20, 'right', duration=2.5)

    # Synchronous arc turn with acceleration smoothing and do not stop at end
    tracks.turn(50, 30, 'left', angle_deg=90, accel=40, accel_interval=0.1, stop_at_end=False)

    # Asynchronous movement with interruption, speed query, and acceleration smoothing:
    async def main():
        tracks = Tracks()
        move_task = asyncio.create_task(tracks.move_async(80, 80, duration=10, accel=40))
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
            tracks.stop()
            print("Tracks stopped.")

        # Asynchronous move for a distance
        await tracks.move_async(80, 80, distance_cm=150, accel=40)

        # Asynchronous turn: spin in place 90 degrees left
        await tracks.turn_async(70, 0, 'left', angle_deg=90)

        # Asynchronous arc turn with acceleration smoothing, do not stop at end
        await tracks.turn_async(40, 30, 'left', angle_deg=45, accel=30, accel_interval=0.05, stop_at_end=False)

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

    DEFAULT_PWM_FW_MIN: int = 307
    DEFAULT_PWM_FW_MAX: int = 217
    DEFAULT_PWM_STOP: int = 318
    DEFAULT_PWM_REV_MIN: int = 329
    DEFAULT_PWM_REV_MAX: int = 419
    DEFAULT_LEFT_CHANNEL: int = 8
    DEFAULT_LEFT_CHANNEL_REVERSE: bool = True
    DEFAULT_RIGHT_CHANNEL: int = 9
    DEFAULT_RIGHT_CHANNEL_REVERSE: bool = False
    DEFAULT_MOVE_DURATION_MAX: int = 10  # Maximum allowed duration in seconds
    DEFAULT_TRACK_WIDTH_CM: float = 19.0  # Distance between tracks in cm (adjust as needed)

    # Calibration defaults
    DEFAULT_BASE_SPEED: int = 70         # Calibration base speed as a percentage
    DEFAULT_BASE_DISTANCE: float = 30.0  # Calibration base distance in centimeters
    DEFAULT_BASE_DURATION: float = 3.5   # Calibration base duration in seconds

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

        # Instance variables for configuration, initialized to defaults
        self.pwm_fw_min: int = self.DEFAULT_PWM_FW_MIN
        self.pwm_fw_max: int = self.DEFAULT_PWM_FW_MAX
        self.pwm_stop: int = self.DEFAULT_PWM_STOP
        self.pwm_rev_min: int = self.DEFAULT_PWM_REV_MIN
        self.pwm_rev_max: int = self.DEFAULT_PWM_REV_MAX
        self.left_channel: int = self.DEFAULT_LEFT_CHANNEL
        self.left_channel_reverse: bool = self.DEFAULT_LEFT_CHANNEL_REVERSE
        self.right_channel: int = self.DEFAULT_RIGHT_CHANNEL
        self.right_channel_reverse: bool = self.DEFAULT_RIGHT_CHANNEL_REVERSE
        self.move_duration_max: int = self.DEFAULT_MOVE_DURATION_MAX
        self.track_width_cm: float = self.DEFAULT_TRACK_WIDTH_CM

        # Calibration parameters (modifiable at runtime)
        self.base_speed: int = self.DEFAULT_BASE_SPEED
        self.base_distance: float = self.DEFAULT_BASE_DISTANCE
        self.base_duration: float = self.DEFAULT_BASE_DURATION

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

    def sanitize_speed(self, speed: Union[int, float, str]) -> int:
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
            logging.error(f"Could not convert speed value '{speed}' to integer.")
            x = 0
        if x < -100 or x > 100:
            logging.warning(
                f"Speed value {x} out of bounds [-100, 100]; clamping to limits."
            )
        return max(-100, min(100, x))

    def get_pwm_fw_speed(self, speed: Union[int, float, str] = 0) -> int:
        """
        Calculate the PWM value for forward speed.

        Args:
            speed: Speed value (0-100), where 0 is stop and 100 is maximum forward.

        Returns:
            int: PWM value for forward motion.
        """
        x = self.sanitize_speed(speed)
        x = max(0, min(100, x))  # Only allow 0-100 for forward
        if x > 99:
            return self.pwm_fw_max
        elif x < 1:
            return self.pwm_stop
        else:
            return self.pwm_fw_min - round((x * 90) / 100)

    def get_pwm_rev_speed(self, speed: Union[int, float, str] = 0) -> int:
        """
        Calculate the PWM value for reverse speed.

        Args:
            speed: Speed value (0-100), where 0 is stop and 100 is maximum reverse.

        Returns:
            int: PWM value for reverse motion.
        """
        x = self.sanitize_speed(speed)
        x = max(0, min(100, x))  # Only allow 0-100 for reverse
        if x > 99:
            return self.pwm_rev_max
        elif x < 1:
            return self.pwm_stop
        else:
            return self.pwm_rev_min + round((x * 90) / 100)

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
        x = self.sanitize_speed(left_track_speed)
        self._left_track_speed = x  # Track the last commanded speed
        try:
            if self.left_channel_reverse:
                # Invert the logic for reversed channel
                if x < 0:
                    self.pwm.set_pwm(self.left_channel, 0, self.get_pwm_fw_speed(-x))
                else:
                    self.pwm.set_pwm(self.left_channel, 0, self.get_pwm_rev_speed(x))
            else:
                if x < 0:
                    self.pwm.set_pwm(self.left_channel, 0, self.get_pwm_rev_speed(-x))
                else:
                    self.pwm.set_pwm(self.left_channel, 0, self.get_pwm_fw_speed(x))
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
        x = self.sanitize_speed(right_track_speed)
        self._right_track_speed = x  # Track the last commanded speed
        try:
            if self.right_channel_reverse:
                # Invert the logic for reversed channel
                if x < 0:
                    self.pwm.set_pwm(self.right_channel, 0, self.get_pwm_fw_speed(-x))
                else:
                    self.pwm.set_pwm(self.right_channel, 0, self.get_pwm_rev_speed(x))
            else:
                if x < 0:
                    self.pwm.set_pwm(self.right_channel, 0, self.get_pwm_rev_speed(-x))
                else:
                    self.pwm.set_pwm(self.right_channel, 0, self.get_pwm_fw_speed(x))
        except Exception as e:
            logging.error("Failed to set right track PWM: %s", e)
            raise TracksError(f"Failed to set right track PWM: {e}")

    def sanitize_duration(self, duration: float) -> float:
        """
        Validate and clamp the duration for movement.

        Args:
            duration: Duration in seconds.

        Returns:
            float: Validated duration, clamped to (0, move_duration_max].

        Raises:
            TracksError: If duration is not a positive float or cannot be converted.
        """
        try:
            d = float(duration)
        except (ValueError, TypeError):
            logging.error(f"Could not convert duration value '{duration}' to float.")
            raise TracksError("Duration must be a number.")
        if d <= 0 or d > self.move_duration_max:
            logging.warning(
                f"Duration value {d} out of bounds (0, {self.move_duration_max}]; "
                f"clamping to limits."
            )
        # Clamp to valid range (0, move_duration_max]
        d_clamped = min(max(d, 0.01), self.move_duration_max)
        return round(d_clamped, 2)

    def _move_duration(
        self,
        left_speed: int,
        right_speed: int,
        distance_cm: float,
    ) -> float:
        """
        Calculate duration needed to move a given distance at specified track speeds.

        Uses calibration: at base_speed, base_duration moves base_distance.

        Args:
            left_speed: Speed for the left track (-100 to 100).
            right_speed: Speed for the right track (-100 to 100).
            distance_cm: Distance to move in centimeters.

        Returns:
            Duration in seconds, clamped to [0.1, move_duration_max].

        Raises:
            TracksError: If both speeds are zero or distance is invalid.
        """
        if distance_cm <= 0:
            raise TracksError("distance_cm must be positive.")
        base_cm_per_sec = self.base_distance / self.base_duration
        v_l = abs(left_speed) * (base_cm_per_sec / self.base_speed)
        v_r = abs(right_speed) * (base_cm_per_sec / self.base_speed)
        avg_cm_per_sec = (v_l + v_r) / 2
        if avg_cm_per_sec == 0:
            raise TracksError("Both track speeds are zero; cannot move a distance.")
        duration = distance_cm / avg_cm_per_sec
        orig_duration = duration
        duration = max(0.1, min(float(self.move_duration_max), float(duration)))
        if duration != orig_duration:
            logging.warning(
                f"Move duration {orig_duration:.2f}s clamped to {duration:.2f}s "
                f"(limits: 0.1s to {self.move_duration_max}s)."
            )
        return duration

    def _move_duration_with_accel(
        self,
        left_start: int,
        right_start: int,
        left_target: int,
        right_target: int,
        distance_cm: float,
        accel: float,
    ) -> float:
        """
        Calculate duration needed to move a given distance with acceleration from start to target speeds.

        Args:
            left_start: Starting speed for the left track (-100 to 100).
            right_start: Starting speed for the right track (-100 to 100).
            left_target: Target speed for the left track (-100 to 100).
            right_target: Target speed for the right track (-100 to 100).
            distance_cm: Distance to move in centimeters.
            accel: Acceleration in percent per second.

        Returns:
            Duration in seconds, clamped to [0.1, move_duration_max].

        Raises:
            TracksError: If both speeds are zero or distance/accel is invalid.
        """
        if distance_cm <= 0:
            raise TracksError("distance_cm must be positive.")
        if accel <= 0:
            raise TracksError("Acceleration must be positive.")

        base_cm_per_sec = self.base_distance / self.base_duration
        v0_l = abs(left_start) * (base_cm_per_sec / self.base_speed)
        v0_r = abs(right_start) * (base_cm_per_sec / self.base_speed)
        v1_l = abs(left_target) * (base_cm_per_sec / self.base_speed)
        v1_r = abs(right_target) * (base_cm_per_sec / self.base_speed)
        v0 = (v0_l + v0_r) / 2
        v1 = (v1_l + v1_r) / 2

        accel_cms2 = abs(accel) * (base_cm_per_sec / self.base_speed)

        # If acceleration is very high, the ramp is nearly instantaneous.
        # If the required distance to accelerate is greater than the total distance,
        # we never reach target speed and must solve for t in s = v0*t + 0.5*a*t^2.
        if accel_cms2 > 0:
            t_accel = abs(v1 - v0) / accel_cms2
            d_accel = (v0 + v1) / 2 * t_accel
            if d_accel >= distance_cm:
                # The distance is too short to reach target speed; solve quadratic:
                # s = v0*t + 0.5*a*t^2  => 0.5*a*t^2 + v0*t - distance_cm = 0
                a = 0.5 * accel_cms2
                b = v0
                c = -distance_cm
                discriminant = b**2 - 4*a*c
                if discriminant < 0:
                    raise TracksError("No real solution for move duration with given parameters.")
                t = (-b + math.sqrt(discriminant)) / (2*a)
                duration = t
            else:
                # Accelerate to target speed, then continue at constant speed
                d_const = max(0, distance_cm - d_accel)
                t_const = d_const / v1 if v1 > 0 else 0
                duration = t_accel + t_const
        else:
            # No acceleration, just use constant speed
            duration = distance_cm / v1 if v1 > 0 else 0

        orig_duration = duration
        duration = max(0.1, min(float(self.move_duration_max), float(duration)))
        if duration != orig_duration:
            logging.warning(
                f"Move duration {orig_duration:.2f}s clamped to {duration:.2f}s "
                f"(limits: 0.1s to {self.move_duration_max}s)."
            )
        return duration

    def move(
        self,
        left_track_speed: Union[int, float, str],
        right_track_speed: Union[int, float, str],
        duration: Optional[float] = None,
        distance_cm: Optional[float] = None,
        accel: Optional[float] = None,
        accel_interval: float = 0.05,
        stop_at_end: bool = True,
    ) -> None:
        """
        Move both tracks at specified speeds for a given duration or distance, with optional acceleration smoothing.

        Either `duration` or `distance_cm` must be provided (not both).

        Args:
            left_track_speed: Speed for the left track (-100 to 100, zero allowed for stopping).
            right_track_speed: Speed for the right track (-100 to 100, zero allowed for stopping).
            duration: Duration in seconds (positive float, max 2 decimal places, <= MOVE_DURATION_MAX).
            distance_cm: Distance to travel in centimeters (positive float).
            accel: Optional acceleration in percent per second (e.g., 100 for full speed in 1s).
                   If None or <= 0, jumps instantly to target speed.
            accel_interval: Time step for acceleration smoothing in seconds.
            stop_at_end: If True (default), stop both tracks at the end. If False, leave tracks running.

        Raises:
            TracksError: If neither or both of duration and distance_cm are provided, or if parameters are invalid.

        Examples:
            tracks.move(80, 80, duration=5, accel=80, accel_interval=0.1)
            tracks.move(80, 80, distance_cm=100)
        """
        if (duration is None and distance_cm is None) or (duration is not None and distance_cm is not None):
            raise TracksError("Exactly one of duration or distance_cm must be provided.")

        left_target = self.sanitize_speed(left_track_speed)
        right_target = self.sanitize_speed(right_track_speed)

        # Calculate duration if distance_cm is given
        if distance_cm is not None:
            if accel is not None and accel > 0:
                left_start = self.get_left_track_speed()
                right_start = self.get_right_track_speed()
                duration_val = self._move_duration_with_accel(
                    left_start, right_start, left_target, right_target, float(distance_cm), float(accel)
                )
            else:
                duration_val = self._move_duration(left_target, right_target, float(distance_cm))
        else:
            duration_val = self.sanitize_duration(duration)

        # Clamp duration to [0.1, move_duration_max]
        orig_duration = duration_val
        duration_val = max(0.1, min(float(self.move_duration_max), float(duration_val)))
        if duration_val != orig_duration:
            logging.warning(
                f"Move duration {orig_duration:.2f}s clamped to {duration_val:.2f}s "
                f"(limits: 0.1s to {self.move_duration_max}s)."
            )

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
        if accel_interval_val <= 0 or accel_interval_val > duration_val:
            raise TracksError("Acceleration interval (accel_interval) must be > 0 and <= duration.")

        # Use current speeds as starting point for ramping
        left_start = self.get_left_track_speed()
        right_start = self.get_right_track_speed()

        try:
            if accel_val is None or accel_val <= 0:
                # No smoothing, jump to target
                logging.debug(f"Jumping to target speeds: left={left_target}, right={right_target}, for={duration_val:03.2f} seconds")
                self.set_left_track_speed(left_target)
                self.set_right_track_speed(right_target)
                time.sleep(duration_val)
            else:
                # Smooth acceleration from current speed to target speed
                logging.debug(f"Smoothly accelerating to target speeds: left={left_target}, right={right_target}, for={duration_val:03.2f} seconds with accel={accel_val}%")
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
                total_steps = max(1, int(duration_val / accel_interval_val))
                steps = min(steps, total_steps)
                for i in range(steps):
                    frac = (i + 1) / steps
                    left = round(left_start + (left_target - left_start) * frac)
                    right = round(right_start + (right_target - right_start) * frac)
                    self.set_left_track_speed(left)
                    self.set_right_track_speed(right)
                    time.sleep(accel_interval_val)
                # Hold at target for the remainder
                remaining = duration_val - steps * accel_interval_val
                if remaining > 0:
                    self.set_left_track_speed(left_target)
                    self.set_right_track_speed(right_target)
                    time.sleep(remaining)
            if stop_at_end:
                self.stop()
        except Exception as e:
            self.stop()
            logging.error("Failed to move tracks: %s", e)
            raise TracksError(f"Failed to move tracks: {e}")

    async def move_async(
        self,
        left_track_speed: Union[int, float, str],
        right_track_speed: Union[int, float, str],
        duration: Optional[float] = None,
        distance_cm: Optional[float] = None,
        accel: Optional[float] = None,
        accel_interval: float = 0.05,
        stop_at_end: bool = True,
    ) -> None:
        """
        Asynchronously move both tracks at specified speeds for a given duration or distance,
        with optional acceleration smoothing.

        Either `duration` or `distance_cm` must be provided (not both).

        This method can be cancelled (e.g., via asyncio.Task.cancel()), but will only stop the tracks
        if the duration completes or an exception occurs. If cancelled, the tracks will continue
        running at the last set speed.

        Args:
            left_track_speed: Target speed for the left track (-100 to 100, zero allowed for stopping).
            right_track_speed: Target speed for the right track (-100 to 100, zero allowed for stopping).
            duration: Duration in seconds (positive float, <= MOVE_DURATION_MAX).
            distance_cm: Distance to travel in centimeters (positive float).
            accel: Optional acceleration in percent per second (e.g., 100 for full speed in 1s).
                   If None, jumps instantly to target speed.
            accel_interval: Time step for acceleration smoothing in seconds.
            stop_at_end: If True (default), stop both tracks at the end. If False, leave tracks running.

        Raises:
            TracksError: If neither or both of duration and distance_cm are provided, or if parameters are invalid.
            asyncio.CancelledError: If the move is interrupted (tracks will NOT be stopped).

        Examples:
            await tracks.move_async(80, 80, distance_cm=100, accel=40)
            await tracks.move_async(80, 80, duration=5, stop_at_end=False)
        """
        if (duration is None and distance_cm is None) or (duration is not None and distance_cm is not None):
            raise TracksError("Exactly one of duration or distance_cm must be provided.")

        left_target = self.sanitize_speed(left_track_speed)
        right_target = self.sanitize_speed(right_track_speed)

        # Calculate duration if distance_cm is given
        if distance_cm is not None:
            if accel is not None and accel > 0:
                left_start = self.get_left_track_speed()
                right_start = self.get_right_track_speed()
                duration_val = self._move_duration_with_accel(
                    left_start, right_start, left_target, right_target, float(distance_cm), float(accel)
                )
            else:
                duration_val = self._move_duration(left_target, right_target, float(distance_cm))
        else:
            duration_val = self.sanitize_duration(duration)

        # Clamp duration to [0.1, move_duration_max]
        orig_duration = duration_val
        duration_val = max(0.1, min(float(self.move_duration_max), float(duration_val)))
        if duration_val != orig_duration:
            logging.warning(
                f"Move duration {orig_duration:.2f}s clamped to {duration_val:.2f}s "
                f"(limits: 0.1s to {self.move_duration_max}s)."
            )

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
        if accel_interval_val <= 0 or accel_interval_val > duration_val:
            raise TracksError("Acceleration interval (accel_interval) must be > 0 and <= duration.")

        # Use current speeds as starting point for ramping
        left_start = self.get_left_track_speed()
        right_start = self.get_right_track_speed()

        try:
            if accel_val is None or accel_val <= 0:
                # No smoothing, jump to target
                logging.debug(f"Jumping to target speeds: left={left_target}, right={right_target}, for={duration_val:03.2f} seconds")
                self.set_left_track_speed(left_target)
                self.set_right_track_speed(right_target)
                await asyncio.sleep(duration_val)
            else:
                # Smooth acceleration from current speed to target speed
                logging.debug(f"Smoothly accelerating to target speeds: left={left_target}, right={right_target}, for={duration_val:03.2f} seconds with accel={accel_val}%")
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
                total_steps = max(1, int(duration_val / accel_interval_val))
                steps = min(steps, total_steps)
                for i in range(steps):
                    frac = (i + 1) / steps
                    left = round(left_start + (left_target - left_start) * frac)
                    right = round(right_start + (right_target - right_start) * frac)
                    self.set_left_track_speed(left)
                    self.set_right_track_speed(right)
                    await asyncio.sleep(accel_interval_val)
                # Hold at target for the remainder
                remaining = duration_val - steps * accel_interval_val
                if remaining > 0:
                    self.set_left_track_speed(left_target)
                    self.set_right_track_speed(right_target)
                    await asyncio.sleep(remaining)
            if stop_at_end:
                self.stop()
        except Exception as e:
            self.stop()
            raise TracksError(f"Failed to move tracks: {e}")

    def turn(
        self,
        speed: Union[int, float, str],
        radius_cm: float,
        direction: str,
        duration: Optional[float] = None,
        angle_deg: Optional[float] = None,
        accel: Optional[float] = None,
        accel_interval: float = 0.05,
        stop_at_end: bool = True,
    ) -> None:
        """
        Turn the rover along an arc or in place, specifying speed, turning radius, and direction.
        Either duration or angle_deg must be provided to define the turn.

        The method computes the correct speed for each track based on the specified radius and direction,
        using differential drive kinematics. If angle_deg is specified, the duration is calculated using
        the calibration: at speed 70, 3.5 seconds moves the rover 30 cm forward.

        Args:
            speed: Overall speed (-100 to 100, positive = forward, negative = reverse, zero allowed for stopping).
            radius_cm: Turning radius in centimeters (0 = spin in place, >0 = arc turn).
            direction: 'left' or 'right'.
            duration: Duration of the turn in seconds. Required if angle_deg is not given.
            angle_deg: Angle to turn in degrees (e.g., 180 for half-turn). Required if duration is not given.
            accel: Optional acceleration for smoothing (percent per second).
            accel_interval: Acceleration interval in seconds.
            stop_at_end: If True (default), stop both tracks at the end. If False, leave tracks running.

        Raises:
            TracksError: On invalid parameters.

        Examples:
            tracks.turn(70, 0, 'left', angle_deg=180)  # Spin in place 180 degrees left
            tracks.turn(60, 20, 'right', duration=2.5) # Arc right for 2.5 seconds
            tracks.turn(50, 30, 'left', angle_deg=90, accel=40, accel_interval=0.1, stop_at_end=False)
        """
        if direction not in ("left", "right"):
            raise TracksError("Direction must be 'left' or 'right'.")
        speed_val = self.sanitize_speed(speed)
        # Clamp target speed to [5, 100] for turns, with warning
        orig_speed_val = speed_val
        if abs(speed_val) < 5 and abs(speed_val) != 0:
            speed_val = 5 if speed_val > 0 else -5
            logging.warning(
                f"Turn speed value {orig_speed_val} clamped to {speed_val} for safe turn duration."
            )
        if radius_cm < 0:
            raise TracksError("Radius must be >= 0.")

        # Calculate duration if angle_deg is given
        if angle_deg is not None:
            if duration is not None:
                raise TracksError("Specify only one of duration or angle_deg.")
            if accel is not None and accel > 0:
                # Use current arc speed as start speed for acceleration-aware duration
                start_speed = self._current_arc_speed_percent(radius_cm)
                duration = self._turn_duration_for_angle_with_accel(
                    start_speed,
                    abs(speed_val),
                    radius_cm,
                    abs(angle_deg),
                    accel,
                )
            else:
                duration = self._turn_duration_for_angle(
                    abs(speed_val), radius_cm, abs(angle_deg)
                )
        if duration is None:
            raise TracksError("Must specify either duration or angle_deg.")

        # Compute track speeds
        left_speed, right_speed = self._track_speeds_for_turn(
            speed_val, radius_cm, direction
        )
        self.move(
            left_speed,
            right_speed,
            duration,
            accel=accel,
            accel_interval=accel_interval,
            stop_at_end=stop_at_end,
        )

    async def turn_async(
        self,
        speed: Union[int, float, str],
        radius_cm: float,
        direction: str,
        duration: Optional[float] = None,
        angle_deg: Optional[float] = None,
        accel: Optional[float] = None,
        accel_interval: float = 0.05,
        stop_at_end: bool = True,
    ) -> None:
        """
        Asynchronously turn the rover along an arc or in place, specifying speed, turning radius, and direction.
        Either duration or angle_deg must be provided to define the turn.

        The method computes the correct speed for each track based on the specified radius and direction,
        using differential drive kinematics. If angle_deg is specified, the duration is calculated using
        the calibration: at speed 70, 3.5 seconds moves the rover 30 cm forward.

        Args:
            speed: Overall speed (-100 to 100, positive = forward, negative = reverse, zero allowed for stopping).
            radius_cm: Turning radius in centimeters (0 = spin in place, >0 = arc turn).
            direction: 'left' or 'right'.
            duration: Duration of the turn in seconds. Required if angle_deg is not given.
            angle_deg: Angle to turn in degrees (e.g., 180 for half-turn). Required if duration is not given.
            accel: Optional acceleration for smoothing (percent per second).
            accel_interval: Acceleration interval in seconds.
            stop_at_end: If True (default), stop both tracks at the end. If False, leave tracks running.

        Raises:
            TracksError: On invalid parameters.

        Examples:
            await tracks.turn_async(70, 0, 'left', angle_deg=90)
            await tracks.turn_async(60, 20, 'right', duration=2.5)
            await tracks.turn_async(40, 30, 'left', angle_deg=45, accel=30, accel_interval=0.05, stop_at_end=False)
        """
        if direction not in ("left", "right"):
            raise TracksError("Direction must be 'left' or 'right'.")
        speed_val = self.sanitize_speed(speed)
        # Clamp target speed to [5, 100] for turns, with warning
        orig_speed_val = speed_val
        if abs(speed_val) < 5 and abs(speed_val) != 0:
            speed_val = 5 if speed_val > 0 else -5
            logging.warning(
                f"Turn speed value {orig_speed_val} clamped to {speed_val} for safe turn duration."
            )
        # Allow zero speed for decelerating to stop or stopping in place
        if radius_cm < 0:
            raise TracksError("Radius must be >= 0.")

        # Calculate duration if angle_deg is given
        if angle_deg is not None:
            if duration is not None:
                raise TracksError("Specify only one of duration or angle_deg.")
            if accel is not None and accel > 0:
                # Use current arc speed as start speed for acceleration-aware duration
                start_speed = self._current_arc_speed_percent(radius_cm)
                duration = self._turn_duration_for_angle_with_accel(
                    start_speed,
                    abs(speed_val),
                    radius_cm,
                    abs(angle_deg),
                    accel,
                )
            else:
                duration = self._turn_duration_for_angle(
                    abs(speed_val), radius_cm, abs(angle_deg)
                )
        if duration is None:
            raise TracksError("Must specify either duration or angle_deg.")

        # Compute track speeds
        left_speed, right_speed = self._track_speeds_for_turn(
            speed_val, radius_cm, direction
        )
        await self.move_async(
            left_speed,
            right_speed,
            duration,
            accel=accel,
            accel_interval=accel_interval,
            stop_at_end=stop_at_end,
        )

    def stop(self) -> None:
        """
        Immediately stop both tracks by setting their speeds to zero.

        Example:
            tracks.stop()
        """
        self.set_left_track_speed(0)
        self.set_right_track_speed(0)

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

        Example:
            tracks._track_speeds_for_turn(70, 0, "left")   # (-70, 70)
            tracks._track_speeds_for_turn(70, 20, "right") # (84, 56)
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

        Uses calibration: at speed 70, 3.5s moves the rover 30 cm forward.

        Args:
            speed: Absolute speed (1-100).
            radius_cm: Turning radius in cm (0 = spin in place).
            angle_deg: Angle to turn in degrees.

        Returns:
            Duration in seconds.

        Raises:
            TracksError: If speed is zero.

        Example:
            tracks._turn_duration_for_angle(70, 0, 180)   # Duration for 180 deg spin in place
            tracks._turn_duration_for_angle(70, 20, 90)   # Duration for 90 deg arc turn
        """
        if speed == 0:
            raise TracksError("Speed must be non-zero for turn duration calculation.")

        # Clamp speed to [5, 100] with warning
        orig_speed = speed
        speed = max(5, min(100, abs(speed)))
        if speed != abs(orig_speed):
            logging.warning(
                f"Speed value {orig_speed} clamped to {speed} for turn duration calculation."
            )

        # Calibration: at speed 70, 3.5s -> 30cm straight
        base_cm_per_sec = self.base_distance / self.base_duration
        cm_per_sec = speed * (base_cm_per_sec / self.base_speed)
        if radius_cm == 0:
            arc_len = self.track_width_cm * math.pi * (angle_deg / 360)
            duration = arc_len / cm_per_sec
        else:
            arc_len = 2 * math.pi * radius_cm * (angle_deg / 360)
            duration = arc_len / cm_per_sec

        # Clamp duration to [0.1, move_duration_max] with warning
        orig_duration = duration
        duration = max(0.1, min(float(self.move_duration_max), float(duration)))
        if duration != orig_duration:
            logging.warning(
                f"Turn duration {orig_duration:.2f}s clamped to {duration:.2f}s "
                f"(limits: 0.1s to {self.move_duration_max}s)."
            )
        return float(duration)

    def _turn_duration_for_angle_with_accel(
        self,
        start_speed: int,
        target_speed: int,
        radius_cm: float,
        angle_deg: float,
        accel: float,
    ) -> float:
        """
        Estimate duration needed to turn a given angle, accounting for acceleration from start_speed
        to target_speed at the specified acceleration rate.

        Args:
            start_speed: Starting speed (absolute value, 1-100).
            target_speed: Target speed (absolute value, 1-100).
            radius_cm: Turning radius in cm (0 = spin in place).
            angle_deg: Angle to turn in degrees.
            accel: Acceleration in percent per second (e.g., 40 means 40% per second).

        Returns:
            Estimated duration in seconds.

        Raises:
            TracksError: If accel <= 0 or speeds are invalid.
        """
        if target_speed == 0 or accel <= 0:
            raise TracksError("Target speed and acceleration must be positive for duration estimation.")

        # Clamp speeds to [5, 100] with warning
        orig_start_speed = start_speed
        orig_target_speed = target_speed
        # Only clamp start_speed if not zero
        if start_speed != 0:
            start_speed = max(5, min(100, abs(start_speed)))
            if start_speed != abs(orig_start_speed):
                logging.warning(
                    f"Start speed value {orig_start_speed} clamped to {start_speed} for turn duration with accel."
                )
        else:
            start_speed = 0
        target_speed = max(5, min(100, abs(target_speed)))
        if target_speed != abs(orig_target_speed):
            logging.warning(
                f"Target speed value {orig_target_speed} clamped to {target_speed} for turn duration with accel."
            )

        # Calibration: at speed 70, 3.5s -> 30cm straight
        base_cm_per_sec = self.base_distance / self.base_duration
        v0 = start_speed * (base_cm_per_sec / self.base_speed)
        v1 = target_speed * (base_cm_per_sec / self.base_speed)

        if radius_cm == 0:
            arc_len = self.track_width_cm * math.pi * (angle_deg / 360)
        else:
            arc_len = 2 * math.pi * radius_cm * (angle_deg / 360)

        # Convert accel from percent/sec to cm/s^2
        accel_cms2 = abs(accel) * (base_cm_per_sec / self.base_speed)

        # If acceleration is very high, the ramp is nearly instantaneous.
        # If the required distance to accelerate is greater than the arc length,
        # we never reach target speed and must solve for t in s = v0*t + 0.5*a*t^2.
        if accel_cms2 > 0:
            t_accel = abs(v1 - v0) / accel_cms2
            d_accel = (v0 + v1) / 2 * t_accel
            if d_accel >= arc_len:
                # The arc is too short to reach target speed; solve quadratic:
                # s = v0*t + 0.5*a*t^2  => 0.5*a*t^2 + v0*t - arc_len = 0
                a = 0.5 * accel_cms2
                b = v0
                c = -arc_len
                discriminant = b**2 - 4*a*c
                if discriminant < 0:
                    raise TracksError("No real solution for turn duration with given parameters.")
                t = (-b + math.sqrt(discriminant)) / (2*a)
                duration = t
            else:
                # Accelerate to target speed, then continue at constant speed
                d_const = max(0, arc_len - d_accel)
                t_const = d_const / v1 if v1 > 0 else 0
                duration = t_accel + t_const
        else:
            # No acceleration, just use constant speed
            duration = arc_len / v1 if v1 > 0 else 0

        # Clamp duration to [0.1, move_duration_max] with warning
        orig_duration = duration
        duration = max(0.1, min(float(self.move_duration_max), float(duration)))
        if duration != orig_duration:
            logging.warning(
                f"Turn duration {orig_duration:.2f}s clamped to {duration:.2f}s "
                f"(limits: 0.1s to {self.move_duration_max}s)."
            )
        return float(duration)

    def _current_arc_speed_cm_s(self, radius_cm: float) -> float:
        """
        Compute the current speed along the arc for the given radius, based on current track speeds.

        Args:
            radius_cm: Turning radius in cm (0 = spin in place).

        Returns:
            float: Current speed along the arc in cm/s.
        """
        base_cm_per_sec = self.base_distance / self.base_duration
        v_l = self.get_left_track_speed() * (base_cm_per_sec / self.base_speed)
        v_r = self.get_right_track_speed() * (base_cm_per_sec / self.base_speed)
        w = self.track_width_cm
        if radius_cm == 0:
            # For spin in place, use the average of the absolute values
            return (abs(v_l) + abs(v_r)) / 2
        # For arc, use the average of the two tracks
        return (v_l + v_r) / 2

    def _current_arc_speed_percent(self, radius_cm: float) -> float:
        """
        Compute the current speed along the arc for the given radius as a percentage (0-100),
        compatible with the rest of the code.

        Args:
            radius_cm: Turning radius in cm (0 = spin in place).

        Returns:
            float: Current arc speed as a percentage (0-100).
        """
        base_cm_per_sec = self.base_distance / self.base_duration
        arc_speed_cm_s = self._current_arc_speed_cm_s(radius_cm)
        # Convert cm/s back to percent of base speed
        arc_speed_percent = (arc_speed_cm_s / base_cm_per_sec) * self.base_speed
        # Clamp to [0, 100]
        return max(0.0, min(100.0, abs(arc_speed_percent)))

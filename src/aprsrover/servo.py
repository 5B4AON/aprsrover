"""
servo.py - Standard hobby servo control utilities using PWM

This module provides the Servo class for controlling standard hobby servo motors
using a PWM controller (such as Adafruit PCA9685).

Features:

- Set servo angle in degrees (with configurable min/max angle and PWM pulse range)
- Specify speed (degrees per second) for smooth movement to target angle
- Synchronous and asynchronous APIs: `set_angle()` and `set_angle_async()`
- Query current angle with `get_angle()`
- Input validation and custom exceptions
- Hardware access is abstracted for easy mocking in tests
- Designed for use with Adafruit PCA9685 PWM driver or a custom/mock PWM controller

Requires:

- Python 3.10+
- Adafruit-PCA9685

Usage example:

    from aprsrover.servo import Servo
    import asyncio

    servo = Servo(channel=0)
    servo.set_angle(90)  # Move instantly to 90 degrees
    servo.set_angle(0, speed=60)  # Move to 0 degrees at 60 deg/sec

    async def main():
        await servo.set_angle_async(180, speed=30)  # Move to 180 deg at 30 deg/sec (async)

See the README.md for more usage examples and parameter details.

Dependencies:
    - Adafruit-PCA9685

This module is designed to be imported and used from other Python scripts.

"""

import asyncio
import logging
import time
from typing import Optional, Protocol, Union

__all__ = ["Servo", "ServoError", "PWMControllerInterface"]


class ServoError(Exception):
    """Custom exception for Servo-related errors."""
    pass


class PWMControllerInterface(Protocol):
    """
    Protocol for PWM controller to allow dependency injection and testing.

    Methods:
        set_pwm(channel: int, on: int, off: int): Set PWM value for a channel.
    """
    def set_pwm(self, channel: int, on: int, off: int) -> None:
        ...


class Servo:
    """
    Controls a standard hobby servo motor using a PWM controller.

    Provides synchronous and asynchronous methods to set servo angle,
    with optional speed (degrees per second) for smooth movement.

    All hardware access is abstracted for easy mocking in tests.
    """

    # Typical servo PWM pulse range (in ticks for PCA9685 at 50Hz)
    PWM_MIN: int = 150  # 0 degrees
    PWM_MAX: int = 600  # 180 degrees
    ANGLE_MIN: float = 0.0
    ANGLE_MAX: float = 180.0

    def __init__(
        self,
        channel: int,
        pwm: Optional[PWMControllerInterface] = None,
        angle_min: float = ANGLE_MIN,
        angle_max: float = ANGLE_MAX,
        pwm_min: int = PWM_MIN,
        pwm_max: int = PWM_MAX,
    ) -> None:
        """
        Initialize the Servo controller.

        Args:
            channel: PWM channel number for this servo.
            pwm: Optional PWM controller instance for dependency injection/testing.
            angle_min: Minimum angle in degrees (default 0).
            angle_max: Maximum angle in degrees (default 180).
            pwm_min: PWM value for angle_min (default 150).
            pwm_max: PWM value for angle_max (default 600).

        Raises:
            ServoError: If the PWM controller fails to initialize.
        """
        self.channel = channel
        self.angle_min = angle_min
        self.angle_max = angle_max
        self.pwm_min = pwm_min
        self.pwm_max = pwm_max

        if pwm is not None:
            self.pwm = pwm
        else:
            try:
                import Adafruit_PCA9685
                self.pwm = Adafruit_PCA9685.PCA9685()
            except ImportError as e:
                raise ServoError("Adafruit_PCA9685 not available and no PWM controller provided.") from e

        self._angle: float = angle_min  # Track last commanded angle
        self.init()

    def init(self) -> None:
        """
        Initialize the PWM controller and set frequency.

        Raises:
            ServoError: If the PWM controller fails to initialize.
        """
        try:
            if hasattr(self.pwm, "set_pwm_freq"):
                self.pwm.set_pwm_freq(50)
        except Exception as e:
            logging.error("Failed to initialize PWM controller: %s", e)
            raise ServoError(f"Failed to initialize PWM controller: {e}")

    def get_angle(self) -> float:
        """
        Get the current angle setting for the servo.

        Returns:
            float: The last commanded angle in degrees.
        """
        return self._angle

    def _sanitize_angle(self, angle: Union[int, float, str]) -> float:
        """
        Convert angle to float and clamp to [angle_min, angle_max].

        Args:
            angle: The angle value to sanitize.

        Returns:
            float: Sanitized angle value.
        """
        try:
            x = float(angle)
        except (ValueError, TypeError):
            x = self.angle_min
        return max(self.angle_min, min(self.angle_max, x))

    def _angle_to_pwm(self, angle: float) -> int:
        """
        Convert angle in degrees to PWM value.

        Args:
            angle: Angle in degrees.

        Returns:
            int: PWM value for the given angle.
        """
        frac = (angle - self.angle_min) / (self.angle_max - self.angle_min)
        pwm = self.pwm_min + frac * (self.pwm_max - self.pwm_min)
        return int(round(pwm))

    def set_angle(
        self,
        angle: Union[int, float, str],
        speed: Optional[float] = None,
        step: float = 1.0,
        step_interval: float = 0.02,
    ) -> None:
        """
        Set the servo angle, optionally moving at a specified speed.

        If speed is None or <= 0, the servo jumps instantly to the target angle.
        If speed > 0, the servo moves smoothly at up to `speed` degrees per second.

        Args:
            angle: Target angle in degrees.
            speed: Optional speed in degrees per second (if None or <= 0, jump instantly).
            step: Angle step size for smooth movement (degrees).
            step_interval: Time interval between steps (seconds).

        Raises:
            ServoError: If setting the PWM value fails.

        Examples:
            servo.set_angle(90)
            servo.set_angle(0, speed=60)
        """
        target = self._sanitize_angle(angle)
        current = self.get_angle()

        if speed is None or speed <= 0:
            # Jump instantly
            pwm = self._angle_to_pwm(target)
            try:
                self.pwm.set_pwm(self.channel, 0, pwm)
                self._angle = target
            except Exception as e:
                logging.error("Failed to set servo PWM: %s", e)
                raise ServoError(f"Failed to set servo PWM: {e}")
            return

        # Smooth movement
        delta = target - current
        direction = 1 if delta > 0 else -1
        total_steps = max(1, int(abs(delta) / step))
        step_time = step / speed  # seconds per step

        try:
            for i in range(total_steps):
                current += direction * step
                if (direction > 0 and current > target) or (direction < 0 and current < target):
                    current = target
                pwm = self._angle_to_pwm(current)
                self.pwm.set_pwm(self.channel, 0, pwm)
                self._angle = current
                time.sleep(max(step_time, step_interval))
            # Final position
            pwm = self._angle_to_pwm(target)
            self.pwm.set_pwm(self.channel, 0, pwm)
            self._angle = target
        except Exception as e:
            logging.error("Failed to set servo PWM: %s", e)
            raise ServoError(f"Failed to set servo PWM: {e}")

    async def set_angle_async(
        self,
        angle: Union[int, float, str],
        speed: Optional[float] = None,
        step: float = 1.0,
        step_interval: float = 0.02,
    ) -> None:
        """
        Asynchronously set the servo angle, optionally moving at a specified speed.

        If speed is None or <= 0, the servo jumps instantly to the target angle.
        If speed > 0, the servo moves smoothly at up to `speed` degrees per second.

        Args:
            angle: Target angle in degrees.
            speed: Optional speed in degrees per second (if None or <= 0, jump instantly).
            step: Angle step size for smooth movement (degrees).
            step_interval: Time interval between steps (seconds).

        Raises:
            ServoError: If setting the PWM value fails.
            asyncio.CancelledError: If the movement is interrupted (servo will remain at last set angle).

        Examples:
            await servo.set_angle_async(180, speed=30)
        """
        target = self._sanitize_angle(angle)
        current = self.get_angle()

        if speed is None or speed <= 0:
            # Jump instantly
            pwm = self._angle_to_pwm(target)
            try:
                self.pwm.set_pwm(self.channel, 0, pwm)
                self._angle = target
            except Exception as e:
                logging.error("Failed to set servo PWM: %s", e)
                raise ServoError(f"Failed to set servo PWM: {e}")
            return

        # Smooth movement
        delta = target - current
        direction = 1 if delta > 0 else -1
        total_steps = max(1, int(abs(delta) / step))
        step_time = step / speed  # seconds per step

        try:
            for i in range(total_steps):
                current += direction * step
                if (direction > 0 and current > target) or (direction < 0 and current < target):
                    current = target
                pwm = self._angle_to_pwm(current)
                self.pwm.set_pwm(self.channel, 0, pwm)
                self._angle = current
                await asyncio.sleep(max(step_time, step_interval))
            # Final position
            pwm = self._angle_to_pwm(target)
            self.pwm.set_pwm(self.channel, 0, pwm)
            self._angle = target
        except Exception as e:
            logging.error("Failed to set servo PWM: %s", e)
            raise ServoError(f"Failed to set servo PWM: {e}")
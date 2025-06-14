# Tracks Module Documentation

## Overview
The Tracks module provides utilities for controlling left and right rover tracks using a PWM controller (such as Adafruit PCA9685), supporting both real and dummy backends for testing.

## Features
- Control left and right tracks independently
- Synchronous and asynchronous movement and turning
- Acceleration smoothing, interruption, and stop-at-end options
- Utility functions for speed-to-PWM conversion
- Input validation for all parameters (speed, duration, acceleration, interval, radius, direction)
- Dependency injection for testability (mock or real PWM controller)
- All hardware access is abstracted for easy mocking in tests
- Custom exception: `TracksError`
- Designed for use with Adafruit PCA9685 PWM driver or a custom/mock PWM controller

## Default Parameters and Customization

The `Tracks` class exposes several default parameters as class-level constants (prefixed with `DEFAULT_`), such as PWM ranges, channel numbers, and track geometry. When you instantiate a `Tracks` object, these defaults are copied to instance attributes, which you can modify at runtime to suit your hardware setup.

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
- `DEFAULT_TRACK_WIDTH_CM`: Distance between tracks in centimeters (default: 15.0)

**Changing parameters at runtime:**
You can modify any of these parameters on a `Tracks` instance after construction. For example:

```python
from aprsrover.tracks import Tracks

tracks = Tracks()
tracks.left_channel_reverse = True  # Reverse left track direction
tracks.right_channel = 10           # Use channel 10 for right track
tracks.track_width_cm = 18.5        # Set track width to 18.5 cm
```

## Example Usage

Here is an example of how to use the `Tracks` class in a Python script:

```python
from aprsrover.tracks import Tracks, TracksError
import time

tracks = Tracks()
try:
    tracks.set_left_track_speed(50)
    time.sleep(1)
    tracks.set_left_track_speed(0)
    tracks.set_right_track_speed(-30)
    time.sleep(1)
    tracks.set_right_track_speed(0)
    tracks.move(left_speed=60, right_speed=-60, duration=2.5)
    tracks.move(left_speed=80, right_speed=80, duration=5, accel=80, accel_interval=0.1)
    tracks.move(left_speed=80, right_speed=80, duration=5, stop_at_end=False)
    print("Left speed:", tracks.get_left_track_speed())
    print("Right speed:", tracks.get_right_track_speed())
    tracks.turn(speed=70, radius_cm=0, direction='left', angle_deg=180)
    tracks.turn(speed=60, radius_cm=20, direction='right', duration=2.5)
    tracks.turn(speed=50, radius_cm=30, direction='left', angle_deg=90, accel=40, accel_interval=0.1, stop_at_end=False)
    tracks.stop()
except TracksError as e:
    print(f"Tracks error: {e}")
```

## Dummy PWM Controller Example

To use the `Tracks` class with a dummy PWM controller for testing or simulation, you can define a class that implements the `PWMControllerInterface` and pass an instance of this class to `Tracks`. For example:

```python
from aprsrover.tracks import Tracks, PWMControllerInterface

class DummyPWM(PWMControllerInterface):
    def set_pwm(self, channel: int, on: int, off: int) -> None:
        pass
    def set_pwm_freq(self, freq: int) -> None:
        pass

tracks = Tracks(pwm=DummyPWM())
tracks.set_left_track_speed(50)
```

## Asynchronous Usage Example

The `Tracks` class also supports asynchronous operation. Here is an example of how to use it with Python's `asyncio` module:

```python
import asyncio
from aprsrover.tracks import Tracks

async def main():
    tracks = Tracks()
    move_task = asyncio.create_task(tracks.move_async(80, 80, 10, accel=40))
    await asyncio.sleep(2)
    move_task.cancel()
    try:
        await move_task
    except asyncio.CancelledError:
        tracks.stop()
        print("Tracks stopped.")

asyncio.run(main())
```

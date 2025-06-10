# Servo Module Documentation

## Overview

The `aprsrover.servo` module provides a high-level, testable interface for controlling standard hobby servo motors using a PWM controller such as the Adafruit PCA9685. It supports both synchronous and asynchronous APIs, input validation, and is designed for easy integration and testing with dummy backends.

## Features

- Set servo angle in degrees (configurable min/max angle and PWM pulse range)
- Specify speed (degrees per second) for smooth movement to target angle
- Synchronous (`set_angle`) and asynchronous (`set_angle_async`) APIs
- Query current angle with `get_angle()`
- Input validation and custom exceptions
- Hardware access is abstracted for easy mocking in tests
- Designed for use with Adafruit PCA9685 PWM driver or a custom/mock PWM controller

## Classes

### Servo

```python
from aprsrover.servo import Servo
```

#### Constructor

```python
Servo(
    channel: int,
    pwm: Optional[PWMControllerInterface] = None,
    angle_min: float = 0.0,
    angle_max: float = 180.0,
    pwm_min: int = 150,
    pwm_max: int = 600,
)
```
- `channel`: PWM channel number for this servo.
- `pwm`: Optional PWM controller instance for dependency injection/testing.
- `angle_min`: Minimum angle in degrees (default 0).
- `angle_max`: Maximum angle in degrees (default 180).
- `pwm_min`: PWM value for angle_min (default 150).
- `pwm_max`: PWM value for angle_max (default 600).

#### Methods

- `set_angle(angle, speed=None, step=1.0, step_interval=0.02)`
  - Set the servo angle, optionally moving at a specified speed (degrees/sec).
  - If `speed` is None or <= 0, jumps instantly to the target angle.
  - If `speed` > 0, moves smoothly at up to `speed` degrees/sec.
- `get_angle()`
  - Returns the last commanded angle in degrees.
- `set_angle_async(angle, speed=None, step=1.0, step_interval=0.02)`
  - Asynchronously set the servo angle, optionally moving at a specified speed.

#### Example Usage

Synchronous:
```python
from aprsrover.servo import Servo
servo = Servo(channel=0)
servo.set_angle(90)  # Move instantly to 90 degrees
servo.set_angle(0, speed=60)  # Move to 0 degrees at 60 deg/sec
```

Asynchronous:
```python
import asyncio
from aprsrover.servo import Servo
async def main():
    servo = Servo(channel=1)
    await servo.set_angle_async(180, speed=30)
asyncio.run(main())
```

## Dummy Backend for Testing

For hardware-free testing and examples, use the `DummyPWM` class from `examples.dummies.servo`:

```python
from examples.dummies.servo import DummyPWM
from aprsrover.servo import Servo
pwm = DummyPWM()
servo = Servo(channel=0, pwm=pwm)
servo.set_angle(90)
```

## Error Handling

- All input is validated and clamped to safe ranges.
- Raises `ServoError` for hardware or parameter errors.

## Example Scripts

See `examples/servo/` for:
- Synchronous and asynchronous usage
- Dummy backend usage
- Input validation and error handling
- Async cancellation

## See Also
- [tracks.md](tracks.md) for track control
- [examples/servo/](../examples/servo/) for runnable scripts

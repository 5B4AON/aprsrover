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

The `Tracks` class exposes several default parameters as class-level constants (prefixed with `DEFAULT_`), such as PWM ranges, channel numbers, track geometry, and calibration values. When you instantiate a `Tracks` object, these defaults are copied to instance attributes, which you can modify at runtime to suit your hardware setup or calibration.

### Default Parameters

- `DEFAULT_PWM_FW_MIN`: Minimum PWM value for forward motion (default: 307)
- `DEFAULT_PWM_FW_MAX`: Maximum PWM value for forward motion (default: 217)
- `DEFAULT_PWM_STOP`: PWM value for stop (default: 318)
- `DEFAULT_PWM_REV_MIN`: Minimum PWM value for reverse motion (default: 329)
- `DEFAULT_PWM_REV_MAX`: Maximum PWM value for reverse motion (default: 419)
- `DEFAULT_LEFT_CHANNEL`: PWM channel for the left track (default: 8)
- `DEFAULT_LEFT_CHANNEL_REVERSE`: Whether to reverse the left track direction (default: True)
- `DEFAULT_RIGHT_CHANNEL`: PWM channel for the right track (default: 9)
- `DEFAULT_RIGHT_CHANNEL_REVERSE`: Whether to reverse the right track direction (default: False)
- `DEFAULT_MOVE_DURATION_MAX`: Maximum allowed move duration in seconds (default: 10)
- `DEFAULT_TRACK_WIDTH_CM`: Distance between tracks in centimeters (default: 19.0)
- `DEFAULT_BASE_SPEED`: Calibration base speed as a percentage (default: 70)
- `DEFAULT_BASE_DISTANCE`: Calibration base distance in centimeters (default: 30.0)
- `DEFAULT_BASE_DURATION`: Calibration base duration in seconds (default: 3.5)

### Changing Parameters at Runtime

You can modify any of these parameters on a `Tracks` instance after construction. For example:

```python
from aprsrover.tracks import Tracks

tracks = Tracks()
tracks.left_channel_reverse = True  # Reverse left track direction
tracks.right_channel = 10           # Use channel 10 for right track
tracks.track_width_cm = 18.5        # Set track width to 18.5 cm

# Calibration parameters (affect speed/distance calculations)
tracks.base_speed = 75              # Change calibration base speed
tracks.base_distance = 32.0         # Change calibration base distance
tracks.base_duration = 3.2          # Change calibration base duration
```

This allows you to adapt the library to your specific hardware without subclassing or modifying the source.

---

## Calibration Parameters

The following calibration parameters are used in all distance and duration calculations:

- **`base_speed`** (`int`):  
  The reference speed (as a percentage, 1–100) used for calibration.  
  Default: `70`

- **`base_distance`** (`float`):  
  The distance (in centimeters) the rover travels at `base_speed` in `base_duration` seconds.  
  Default: `30.0`

- **`base_duration`** (`float`):  
  The time (in seconds) it takes to travel `base_distance` at `base_speed`.  
  Default: `3.5`

You can adjust these at runtime to match your hardware's actual performance.

---

## Tracks Class – Rover Track Control

The `Tracks` class provides a high-level interface for controlling the left and right tracks of a rover using a PWM controller (such as the Adafruit PCA9685). It supports both synchronous and asynchronous movement, arc turns, in-place spins, and acceleration smoothing. All hardware access is abstracted for easy mocking in tests.

---

## Features

- **Independent Track Control:**  
  Set speed and direction for each track with `set_left_track_speed()` and `set_right_track_speed()`.
- **Query Current Speeds:**  
  Use `get_left_track_speed()` and `get_right_track_speed()`.
- **Synchronous and Asynchronous Movement:**  
  - `move()` and `move_async()` support optional acceleration smoothing and optional stop at end.
  - **You may specify either a duration (in seconds) or a distance (in centimeters) for the move.**
  - If a distance is specified, the duration is automatically calculated using calibration parameters and the current/target speeds.
- **Arc and In-Place Turns:**  
  - `turn()` and `turn_async()` support both arc and spin-in-place turns, with optional acceleration smoothing.
  - Specify either duration (in seconds) or angle (in degrees) for the turn.
  - Automatically computes correct speed for each track based on radius and direction.
- **Input Validation:**  
  All parameters are validated and clamped as needed.
- **Custom Exception:**  
  All errors raise `TracksError` for granular error handling.
- **Hardware Abstraction:**  
  All hardware access is abstracted for easy mocking in tests.

---

## Moving by Distance

You can command the rover to move a specific distance (in centimeters) instead of a fixed duration. The library will automatically calculate the required duration based on your calibration parameters and the current or target speeds.

### Synchronous Example

```python
from aprsrover.tracks import Tracks

tracks = Tracks()
tracks.move(80, 80, distance_cm=100)  # Move both tracks for 100 cm (duration auto-calculated)
tracks.move(60, 40, distance_cm=50, accel=40)  # Move 50 cm with acceleration smoothing
```

### Asynchronous Example

```python
import asyncio
from aprsrover.tracks import Tracks

async def main():
    tracks = Tracks()
    await tracks.move_async(80, 80, distance_cm=150, accel=40)
    await tracks.move_async(80, 60, distance_cm=75)

asyncio.run(main())
```

### Notes

- You must specify **either** `duration` **or** `distance_cm` (not both).
- If both are provided, a `TracksError` is raised.
- If neither is provided, a `TracksError` is raised.
- The distance is interpreted in centimeters and must be a positive float.
- The duration is calculated using the calibration parameters (`base_speed`, `base_distance`, `base_duration`) and the average of the two track speeds.
- If acceleration is specified, the duration calculation accounts for ramping from the current speed to the target speed.

---

## Usage Example

```python
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

asyncio.run(main())
```

---

## Dependencies

- Python 3.10+
- Adafruit-PCA9685

---

## See Also

- [API Reference](./api.md)
- [Examples](../examples/)
- [README.md](../README.md)

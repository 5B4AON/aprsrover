# Tracks Module Documentation

## Overview
The Tracks module provides utilities for controlling left and right rover tracks using a PWM controller, supporting both real and dummy backends for testing.

## Features
- Control left and right tracks independently
- Synchronous and asynchronous movement and turning
- Acceleration smoothing, interruption, and stop-at-end options
- Utility functions for speed-to-PWM conversion
- Input validation for all parameters
- Dependency injection for testability
- Custom exception: `TracksError`

## Usage
### Basic Example
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
    tracks.move(60, -60, 2.5)
    tracks.move(80, 80, 5, accel=80, accel_interval=0.1)
    tracks.move(80, 80, 5, stop_at_end=False)
    print("Left speed:", tracks.get_left_track_speed())
    print("Right speed:", tracks.get_right_track_speed())
    tracks.turn(70, 0, 'left', angle_deg=180)
    tracks.turn(60, 20, 'right', duration=2.5)
    tracks.turn(50, 30, 'left', angle_deg=90, accel=40, accel_interval=0.1, stop_at_end=False)
    tracks.stop()
except TracksError as e:
    print(f"Tracks error: {e}")
```

### Dummy PWM Example
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

### Asynchronous Example
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

## Notes
- All hardware access is abstracted for easy mocking in tests.
- See the [examples/README.md](../examples/README.md) for more advanced usage scenarios.

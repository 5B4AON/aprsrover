# APRS Rover Library

A modular, testable Python library for controlling a rover using APRS, GPS, GPIO switches, and PWM tracks.  
Designed for easy integration, asynchronous operation, and high testability with abstracted hardware access.

---

## Table of Contents

- [Features Overview](#features-overview)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [GPS Features](#gps-features)
  - [GPS Usage](#gps-usage)
- [Tracks Features](#tracks-features)
  - [Tracks Usage](#tracks-usage)
- [APRS Features](#aprs-features)
  - [APRS Usage](#aprs-usage)
    - [Receiving Frames: Registering Observers and Listening for Messages](#receiving-frames-registering-observers-and-listening-for-messages)
    - [Sending APRS Messages and Object Reports](#sending-aprs-messages-and-object-reports)
- [Switch Features](#switch-features)
  - [Switch Usage](#switch-usage)
- [Examples](#examples)
- [Testing](#testing)
- [Building the package](#building-the-package)
- [Coding Guidelines](#coding-guidelines)
- [License](#license)

---

## Features Overview

- **GPS**: Connect to GPSD, retrieve and format GPS data, with robust error handling.
- **Tracks**: Control rover tracks via PWM, with speed/direction APIs and input validation.
- **APRS**: Interface with KISS TNC, send/receive APRS frames, observer pattern for async frame handling.
- **Switch**: Manage GPIO-connected switches (input/output), observer pattern for state changes, async/sync monitoring.
- **Testing**: All hardware access is abstracted for easy mocking; high test coverage and CI-friendly.
- **Documentation**: Comprehensive usage examples and API documentation.

---

## GPS Features

- Connect to GPSD or inject a custom GPS backend for testing or simulation
- Retrieve and format GPS data in either APRS DMM format or decimal degrees
- Utility functions for coordinate and time formatting
- Custom exception: `GPSError` for granular error handling
- **Dependency injection:** Easily test or simulate GPS by passing a dummy/mock object implementing `GPSDInterface`
- **Fully modular and testable:** All hardware access is abstracted for easy mocking in tests

## GPS Usage

### Using the Real GPSD Backend

```python
from aprsrover.gps import GPS, GPSError

gps = GPS()  # Uses real gpsd if available
try:
    # Get APRS DMM format
    data = gps.get_gps_data_dmm()
    if data is None:
        print("No GPS fix yet. Try running: cgps -s")
    else:
        lat_dmm, lon_dmm, tm, bearing = data
        print("APRS DMM:", lat_dmm, lon_dmm, tm, bearing)
except GPSError as e:
    print(f"GPS error: {e}")
```

### Dummy GPS Example

```python
from aprsrover.gps import GPS, GPSDInterface

class DummyGPSD(GPSDInterface):
    def get_current(self):
        class Packet:
            lat = 51.5
            lon = -0.1
            time = "2024-01-01T12:00:00.000Z"
            mode = 3
            track = 123.4
        return Packet()

gps = GPS(gpsd=DummyGPSD())
lat_dmm, lon_dmm, tm, bearing = gps.get_gps_data_dmm()
print("Dummy DMM:", lat_dmm, lon_dmm, tm, bearing)
```

---

## Tracks Features

- Control left and right rover tracks using a PWM controller
- Set speed and direction for each track independently:
    - `set_left_track_speed()`, `set_right_track_speed()`
    - Query current speed with `get_left_track_speed()`, `get_right_track_speed()`
- Move both tracks simultaneously for a specified duration:
    - Synchronous: `move()` (supports optional acceleration smoothing and **optional stop at end**)
    - Asynchronous: `move_async()` (supports optional acceleration smoothing, interruption, and **optional stop at end**)
- **Turn the rover along an arc or in place, specifying speed, turning radius, and direction:**
    - Synchronous: `turn()` (supports optional acceleration smoothing and **optional stop at end**)
    - Asynchronous: `turn_async()` (supports optional acceleration smoothing, interruption, and **optional stop at end**)
    - Specify either duration (in seconds) or angle (in degrees) for the turn
    - Automatically computes correct speed for each track based on radius and direction
    - Supports acceleration smoothing for turns as well
    - **All movement and turn methods accept a `stop_at_end` parameter (default `True`). If set to `False`, tracks will continue running at the last set speed after the operation completes.**
- Utility functions to convert speed values to PWM signals
- Input validation for speed, duration, acceleration, interval, radius, and direction parameters
- Designed for use with Adafruit PCA9685 PWM driver or a custom/mock PWM controller for testing
- All hardware access is abstracted for easy mocking in tests
- Custom exception: `TracksError` for granular error handling

## Tracks Usage

```python
from aprsrover.tracks import Tracks, TracksError
import time

tracks = Tracks()  # Uses default Adafruit_PCA9685.PCA9685()

try:
    # Move left track forward at 50% speed for 1 second
    tracks.set_left_track_speed(50)
    time.sleep(1)
    tracks.set_left_track_speed(0)

    # Move right track reverse at 30% speed for 1 second
    tracks.set_right_track_speed(-30)
    time.sleep(1)
    tracks.set_right_track_speed(0)

    # Move both tracks: left at 60% forward, right at 60% reverse, for 2.5 seconds (stops at end)
    tracks.move(60, -60, 2.5)

    # Move both tracks with acceleration smoothing (ramps to speed over 1s, holds, then stops)
    tracks.move(80, 80, 5, accel=80, accel_interval=0.1)

    # Move both tracks, but do NOT stop at end (leave tracks running at last speed)
    tracks.move(80, 80, 5, stop_at_end=False)

    # Query current speeds
    print("Left speed:", tracks.get_left_track_speed())
    print("Right speed:", tracks.get_right_track_speed())

    # --- Turn methods ---
    # Spin in place 180 degrees left at speed 70 (stops at end)
    tracks.turn(70, 0, 'left', angle_deg=180)

    # Arc right with radius 20cm for 2.5 seconds at speed 60 (stops at end)
    tracks.turn(60, 20, 'right', duration=2.5)

    # Arc left with radius 30cm for 90 degrees at speed 50, with acceleration smoothing, do NOT stop at end
    tracks.turn(50, 30, 'left', angle_deg=90, accel=40, accel_interval=0.1, stop_at_end=False)

    # Explicitly stop both tracks at any time
    tracks.stop()

except TracksError as e:
    print(f"Tracks error: {e}")
```

### Dummy Tracks (PWM) Example

```python
from aprsrover.tracks import Tracks, PWMControllerInterface

class DummyPWM(PWMControllerInterface):
    def __init__(self):
        self.calls = []
        self.freq = None
    def set_pwm(self, channel: int, on: int, off: int) -> None:
        self.calls.append((channel, on, off))
    def set_pwm_freq(self, freq: int) -> None:
        self.freq = freq

tracks = Tracks(pwm=DummyPWM())
tracks.set_left_track_speed(50)
print("Dummy PWM calls:", tracks._pwm.calls)
```

### Asynchronous Movement, Turning, and Interruption Example

```python
import asyncio
from aprsrover.tracks import Tracks

async def main():
    tracks = Tracks()
    # Start moving both tracks asynchronously for 10 seconds, ramping to 80% speed over 2 seconds
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
        tracks.stop()
        print("Tracks stopped.")

    # --- Asynchronous turn ---
    # Spin in place 90 degrees left at speed 70 (stops at end)
    await tracks.turn_async(70, 0, 'left', angle_deg=90)

    # Arc right with radius 25cm for 1.5 seconds at speed 60 (stops at end)
    await tracks.turn_async(60, 25, 'right', duration=1.5)

    # Arc left with radius 30cm for 45 degrees at speed 40, with acceleration smoothing, do NOT stop at end
    await tracks.turn_async(40, 30, 'left', angle_deg=45, accel=30, accel_interval=0.05, stop_at_end=False)

    # Explicitly stop both tracks at any time
    tracks.stop()

asyncio.run(main())
```

**Note:**  
- All movement and turn methods (`move`, `move_async`, `turn`, `turn_async`) accept a `stop_at_end` parameter (default `True`). If set to `False`, tracks will continue running at the last set speed after the operation completes. Use `tracks.stop()` to stop both tracks explicitly.
- Speed values range from -100 (full reverse) to 100 (full forward).
- Duration for `move()`, `move_async()`, `turn()`, and `turn_async()` must be a positive float ≤ 10 seconds (rounded to 2 decimal places).
- `accel` is in percent per second (e.g., 50 means it takes 2 seconds to go from 0 to 100).
- `accel_interval` controls the smoothness of ramping (default 0.05s, must be > 0 and ≤ duration).
- For `turn()` and `turn_async()`, you must specify either `duration` (in seconds) or `angle_deg` (in degrees, e.g., 180 for half-turn).
- The correct speed for each track is computed automatically based on the specified radius and direction, using differential drive kinematics.
- All inputs are validated and clamped to safe ranges.
- `move_async()` and `turn_async()` can be cancelled (e.g., if an obstacle is detected); tracks will continue at last speed until you explicitly stop them.
- You can inject a custom or dummy PWM controller for testing by passing it to the `Tracks(pwm=...)` constructor.

---

## APRS Features

- Interface with a KISS TNC for APRS frame transmission and reception
- **Dependency injection:** Easily test or simulate APRS by passing a dummy/mock object implementing `KISSInterface`
- Observer pattern: register callback functions to handle incoming frames asynchronously, filtered by callsign
- Send APRS messages and acknowledgements
- Send APRS objects (with validation for all parameters)
- Input validation for observer registration and message/object sending
- Designed for use with `kiss3` and `ax253` libraries
- All hardware access is abstracted for easy mocking in tests
- Custom exception: `AprsError` for granular error handling
- Fully modular and testable

## APRS Usage

### Receiving Frames: Registering Observers and Listening for Messages

```python
from aprsrover.aprs import Aprs
import asyncio

def my_frame_handler(frame):
    print("Received frame:", frame)

async def main():
    aprs = Aprs(host="localhost", port=8001)
    await aprs.connect()  # Establish connection to KISS TNC (async, must be awaited)

    # Register an observer callback for your callsign
    aprs.register_observer("5B4AON-9", my_frame_handler)

    # To register multiple callbacks for the same callsign:
    aprs.register_observer("5B4AON-9", lambda frame: print("Another handler", frame))

    # Start the async frame reception loop (runs forever and notifies observers)
    await aprs.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**Note:**  
- The `connect()` and `run()` methods are asynchronous and must be awaited.
- Observer callbacks must accept a single argument (the received frame).
- You must provide your callsign when registering or unregistering observers.
- Multiple callbacks can be registered for the same callsign.

---

### Sending APRS Messages and Object Reports

```python
from aprsrover.aprs import Aprs
import asyncio

async def main():
    aprs = Aprs(host="localhost", port=8001)
    await aprs.connect()

    # Send a message (with validation)
    aprs.send_my_message_no_ack(
        mycall="5B4AON-7",
        path=["WIDE1-1"],
        recipient="5B4AON-9",
        message="Hello APRS"
    )

    # Send an object (with validation)
    aprs.send_object_report(
        mycall="5B4AON-9",
        path=["WIDE1-1"],
        time_dhm="011234z",           # 6 digits + 'z'
        lat_dmm="5132.07N",           # 7 digits + N/S
        long_dmm="00007.40W",         # DMM format + E/W
        symbol_id="/",                # 1 character
        symbol_code="O",              # 1 character
        comment="Test object"         # up to 43 characters
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Dummy APRS (KISS) Example

```python
from aprsrover.aprs import Aprs, KISSInterface

class DummyKISS(KISSInterface):
    async def create_tcp_connection(self, host, port, kiss_settings):
        class DummyProtocol:
            def write(self, frame): print("Dummy write:", frame)
            async def read(self):
                yield None  # Simulate no frames
        return (None, DummyProtocol())
    def write(self, frame): print("Dummy write:", frame)
    def read(self): yield None

aprs = Aprs(kiss=DummyKISS())
aprs.initialized = True
aprs.kiss_protocol = DummyKISS()  # For direct calls in tests

# Now you can call aprs.send_my_message_no_ack(...) etc. for unit testing without hardware.
```

**Note:**  
- All APRS message/object sending methods validate their parameters and raise exceptions on invalid input.
- Both `mycall` and `recipient` must be 3-6 uppercase alphanumeric characters, a dash, then 1-2 digits (e.g., `5B4AON-9`), with a maximum total length of 9.
- For `send_object_report`, `time_dhm` must be 6 digits followed by 'z' (e.g., '011234z'), and `lat_dmm` must be 7 digits (with optional dot) followed by 'N' or 'S' (e.g., '5132.07N').
- Requires the `kiss3` and `ax253` libraries for KISS TNC and AX.25 frame handling.

---

## Switch Features

- Modular, testable interface for managing GPIO-connected switches on a Raspberry Pi
- Supports both input ("IN") and output ("OUT") switch configurations (set at initialization)
- Provides methods to check the status of a switch (`get_state`) and to set the state for output switches (`set_state`)
- Observer pattern: register callback functions to be notified when a switch changes state (works for both input and output switches)
- Supports both synchronous and asynchronous monitoring of switch state changes
- Input validation for pin numbers, direction, and observer registration
- Abstracts GPIO access for easy testing and mocking (dependency injection via `gpio` parameter)
- Custom exception: `SwitchError` for granular error handling

## Switch Usage

```python
from aprsrover.switch import Switch, SwitchError, SwitchEvent
import time

# Example: Using a GPIO pin as an input switch
switch_in = Switch(pin=17, direction="IN")
def on_switch_change(event: SwitchEvent) -> None:
    print(f"Switch {event.pin} changed to {'ON' if event.state else 'OFF'}")
switch_in.add_observer(on_switch_change)
switch_in.start_monitoring()
time.sleep(5)
switch_in.stop_monitoring()

# Example: Using a GPIO pin as an output switch
switch_out = Switch(pin=18, direction="OUT")
switch_out.set_state(True)   # Turn switch ON
print("Switch state is ON:", switch_out.get_state())
switch_out.set_state(False)  # Turn switch OFF
print("Switch state is OFF:", not switch_out.get_state())

# Observers work for output switches as well
switch_out.add_observer(lambda event: print(f"Output pin {event.pin} is now {'ON' if event.state else 'OFF'}"))
switch_out.set_state(True)
```

### Dummy Switch (GPIO) Example

```python
from aprsrover.switch import Switch, GPIOInterface

class DummyGPIO(GPIOInterface):
    def __init__(self):
        self.states = {}
    def setup(self, pin, direction): self.states[pin] = False
    def input(self, pin): return self.states.get(pin, False)
    def output(self, pin, value): self.states[pin] = value

switch = Switch(pin=17, direction="IN", gpio=DummyGPIO())
print("Dummy switch state:", switch.get_state())
```

**Note:**  
- The `direction` parameter must be either `"IN"` or `"OUT"` and is fixed at initialization.
- For `"OUT"` switches, `set_state()` changes the output and notifies observers if the state changes.
- For `"IN"` switches, `get_state()` returns the current input state (True for ON, False for OFF).
- Observers can be registered for both input and output switches and will be notified on state changes.
- All GPIO access is abstracted for easy mocking in tests; pass a custom `gpio` object for testing.
- All methods are thread-safe and suitable for use in asynchronous or multi-threaded applications.
- Requires `RPi.GPIO` on Raspberry Pi hardware; does not attempt to import GPIO on other platforms.

---

## Examples

See the `examples/` directory for real-world usage scenarios, including:
- Integrating APRS, GPS, and Tracks together for remote rover control and telemetry.
- Registering APRS message callbacks to control rover movement or respond with position.
- Sending an APRS message and object report when the rover arrives at a destination, and periodic object reports as it moves, using decimal coordinates for calculations and DMM/DHM for APRS.

## Project Structure
- `gps.py`: Main GPS utility module
- `tracks.py`: Utility module for controlling rover track motion via PWM
- `aprs.py`: APRS utility module for frame transmission/reception
- `switch.py`: GPIO switch utility module
- `examples/`: Example scripts for integration and real-world usage
- `tests/`: Unit tests

## Requirements
- Python 3.10+
- gpsd-py3
- Adafruit-PCA9685
- kiss3
- ax253

## Installation
```
pip install gpsd-py3
pip install Adafruit-PCA9685
pip install kiss3
pip install ax253

pip install mypy ruff
pip install setuptools
pip install coverage
pip install coverage[toml]
```

## Testing

Run unit tests:  
```sh
python3 -m unittest discover -s tests
```

Run your tests with coverage:  
```sh
coverage run -m unittest discover -s tests
```

View the coverage report in the terminal:  
```sh
coverage report -m
```

Generate an HTML coverage report:  
```sh
coverage html
```
Then open `htmlcov/index.html` in your browser to view detailed coverage.  

Type Checking with mypy:  
```sh
mypy src/
```

Linting with Ruff:  
```sh
ruff check src/
```

Auto-formatting with Ruff (optional):  
```sh
ruff format src/
```

If you want to check your tests as well, add the tests directory:  
```sh
mypy src/ tests/
ruff check src/ tests/
```

## Building the package
```sh
pip install build
python -m build
```
This will create `dist/` with `.tar.gz` (source) and `.whl` (wheel) files.  
Optional: Install your built package locally  
```sh
pip install dist/aprsrover-0.1.0-py3-none-any.whl
```

## Coding Guidelines

This project follows these coding guidelines:

- Code should be modular, testable, and suitable for import and use in other scripts.
- All public functions and classes must use type hints for function signatures.
- All public functions and classes must have clear and concise docstrings.
- Use consistent naming conventions throughout the codebase.
- Avoid global state where possible.
- Follow Python best practices for maintainability and readability.

See the source files for examples of these practices in action.

## License
MIT

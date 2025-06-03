# APRS Rover Library

This package provides utilities for controlling an ROV using APRS.  
It is designed to be imported and used from other Python scripts.  

## GPS Features
- Connect to GPSD
- Retrieve and format GPS data
- Retrieve GPS data in either APRS DMM format or decimal degrees
- Utility functions for coordinate and time formatting
- Custom exception: `GPSError` for granular error handling

## GPS Usage

```python
from aprsrover.gps import GPS, GPSError

gps = GPS()
try:
    gps.connect()
    # Get APRS DMM format for APRS transmission
    lat_dmm, lon_dmm, tm, bearing = gps.get_gps_data_dmm()
    # Get decimal degrees format for calculations
    lat_dec, lon_dec, iso_time, bearing = gps.get_gps_data_decimal()
    print("APRS DMM:", lat_dmm, lon_dmm, tm, bearing)
    print("Decimal:", lat_dec, lon_dec, iso_time, bearing)
except GPSError as e:
    print(f"GPS error: {e}")
```

## Tracks Features

- Control left and right rover tracks using a PWM controller
- Set speed and direction for each track independently
- Move both tracks simultaneously for a specified duration
- Utility functions to convert speed values to PWM signals
- Input validation for speed and duration
- Designed for use with Adafruit PCA9685 PWM driver
- Custom exception: `TracksError` for granular error handling

## Tracks Usage

```python
from aprsrover.tracks import Tracks, TracksError
import time

tracks = Tracks()  # Uses default Adafruit_PCA9685.PCA9685()

try:
    # Move left track forward at 50% speed for 1 second
    tracks.left_track(50)
    time.sleep(1)
    tracks.left_track(0)

    # Move right track reverse at 30% speed for 1 second
    tracks.right_track(-30)
    time.sleep(1)
    tracks.right_track(0)

    # Move both tracks: left at 60% forward, right at 60% reverse, for 2.5 seconds
    tracks.move(60, -60, 2.5)
except TracksError as e:
    print(f"Tracks error: {e}")
```

**Note:**  
- Speed values range from -100 (full reverse) to 100 (full forward).
- Duration for `move()` must be a positive float ≤ 10 seconds (rounded to 2 decimal places).
- All inputs are validated and clamped to safe ranges.

## APRS Features

- Interface with a KISS TNC for APRS frame transmission and reception
- Observer pattern: register callback functions to handle incoming frames asynchronously
- Send APRS messages and acknowledgements
- Send APRS objects (with validation for all parameters)
- Input validation for observer registration and message/object sending
- Designed for use with `kiss3` and `ax253` libraries

## APRS Usage

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

    # To unregister a specific callback:
    aprs.unregister_observer("5B4AON-9", my_frame_handler)

    # To unregister all callbacks for a callsign:
    aprs.unregister_observer("5B4AON-9")

    # To clear all observers:
    aprs.clear_observers()

    # Send a message (with validation)
    aprs.send_my_message_no_ack(
        mycall="5B4AON-7",
        path=["WIDE1-1"],
        recipient="5B4AON-9",
        message="Hello APRS"
    )

    # Send an object (with validation)
    aprs.send_my_object_no_course_speed(
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
    # Run the async main function
    asyncio.run(main())
```

**Note:**  
- Observer callbacks must accept a single argument (the received frame).
- You must provide your callsign when registering or unregistering observers.
- Multiple callbacks can be registered for the same callsign.
- All APRS message/object sending methods validate their parameters and raise exceptions on invalid input.
- For `send_my_object_no_course_speed`, `time_dhm` must be 6 digits followed by 'z' (e.g., '011234z'), and `lat_dmm` must be 7 digits (with optional dot) followed by 'N' or 'S' (e.g., '5132.07N').
- Requires the `kiss3` and `ax253` libraries for KISS TNC and AX.25 frame handling.

## Examples

See the `examples/` directory for real-world usage scenarios, including:
- Integrating APRS, GPS, and Tracks together for remote rover control and telemetry.
- Registering APRS message callbacks to control rover movement or respond with position.
- Sending an APRS message and object report when the rover arrives at a destination, and periodic object reports as it moves, using decimal coordinates for calculations and DMM/DHM for APRS.

## Project Structure
- `gps.py`: Main GPS utility module
- `tracks.py`: Utility module for controlling rover track motion via PWM
- `aprs.py`: APRS utility module for frame transmission/reception
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

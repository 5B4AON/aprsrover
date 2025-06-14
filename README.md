# APRS Rover Library

A modular Python library for controlling a rover using APRS, GPS, GPIO switches, PWM tracks, NeoPixel LEDs, and ultrasonic distance sensors. Designed for easy integration, asynchronous operation, and high testability with abstracted hardware access.

---

## Features Overview

- **GPS**: Connect to GPSD, retrieve and format GPS data, with robust error handling and testable backends.
- **Tracks**: Control rover tracks via PWM, with sync/async APIs, acceleration smoothing, and input validation.
- **APRS**: Interface with KISS TNC, send/receive APRS frames, observer pattern for async frame handling.
- **Switch**: Manage GPIO-connected switches (input/output), observer pattern for state changes, async/sync monitoring.
- **HW Info**: Query CPU temperature, CPU usage, RAM usage, and system uptime with dependency injection for testability.
- **UltraSonic**: Interface with ultrasonic distance sensors (e.g., HC-SR04), supporting sync/async measurement, observer pattern, and dummy/test backends.
- **NeoPixel**: Control WS2812/WS2812B LED strips or rings with sync/async APIs, dummy and hardware backends, and animation support via `NeoPixelAnimator`.
- **Testing**: All hardware access is abstracted for easy mocking; high test coverage and CI-friendly.
- **Documentation**: Comprehensive usage examples and API documentation.

---

## Documentation

- [GPS Module](docs/gps.md)
- [Tracks Module](docs/tracks.md)
- [APRS Module](docs/aprs.md)
- [Switch Module](docs/switch.md)
- [HW Info Module](docs/hw_info.md)
- [UltraSonic Module](docs/ultra.md)
- [Servo Module](docs/servo.md)
- [NeoPixel Module](docs/neopixel.md)
- [Testing Guide](docs/testing.md)
- [Building the Package](docs/building.md)

---

## Examples
See the [examples/](examples/README.md) directory for a wide range of real-world and modular usage scenarios, including:
- Integration of APRS, GPS, Tracks, Switch, HW Info, UltraSonic, Servo, and NeoPixel modules for remote rover control, telemetry, lighting, and system monitoring.
- Synchronous and asynchronous movement and turning with Tracks and Servo, including acceleration smoothing, interruption, and dummy/mock PWM usage.
- Synchronous and asynchronous distance measurement with UltraSonic, including observer registration and dummy/mock GPIO usage.
- Synchronous and asynchronous NeoPixel LED control, including animation with `NeoPixelAnimator`, and dummy/hardware backends for safe testing.
- Registering APRS message callbacks to control rover movement, respond with position or status, and handle acknowledgements.
- Demonstrations of dummy/test backends for GPS, PWM, HW Info, APRS, Switch, UltraSonic, Servo, and NeoPixel modules for safe testing without hardware.
- End-to-end integration scripts combining various modules.
- Example scripts organized by feature and by sync/async usage, with clear separation of dummy and real hardware scenarios.

Browse the `examples/` subfolders for focused demonstrations of each module and integration pattern.

---

## Project Structure
- `src/aprsrover/`: Main library modules
- `examples/`: Example scripts for integration and real-world usage
- `tests/`: Unit tests
- `docs/`: Module and process documentation

## Dependencies
- Python 3.10+
- gpsd-py3
- Adafruit-PCA9685
- kiss3
- ax253
- RPi.GPIO (if running on Raspberry Pi)
- rpi_ws281x

## License
MIT

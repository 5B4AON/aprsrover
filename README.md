# APRS Rover Library

A modular Python library for controlling a rover over APRS.  
Using APRS is optional and does not prevent you from using the library for the rest of its features.  
Designed for easy integration, asynchronous operation, and high testability with abstracted hardware access.  

APRS (Automatic Packet Reporting System) is a digital communication protocol used by amateur radio operators to transmit real-time data such as position, telemetry, and messages over radio. To use the APRS functionality with a radio for over-the-air communication, you must hold a valid Amateur Radio license.

Developed in June 2025, as a STEM project by members of the [Cyprus Amateur Radio Society](https://www.cyhams.org).

---

## Features Overview

- **GPS**: Connect to GPSD, retrieve and format GPS data, with robust error handling and testable backends.
- **Tracks**: Control rover tracks via PWM, with sync/async APIs, acceleration smoothing, and input validation.
- **APRS**: Interface with KISS TNC, send/receive APRS frames, observer pattern for async frame handling.
- **Switch**: Manage GPIO-connected switches (input/output), observer pattern for state changes, async/sync monitoring.
- **HW Info**: Query CPU temperature, CPU usage, RAM usage, and system uptime with dependency injection for testability.
- **UltraSonic**: Interface with ultrasonic distance sensors (e.g., HC-SR04), supporting sync/async measurement, observer pattern, and dummy/test backends.
- **NeoPixel**: Control WS2812/WS2812B LED strips or rings with sync/async APIs, dummy and hardware backends, and animation support via `NeoPixelAnimator`.
- **DHT**: Read temperature and humidity from DHT11/DHT22/AM2302 sensors with sync/async APIs, dummy and hardware backends.
- **Compass**: Read magnetic heading from HMC5883L sensors with sync/async APIs, dummy and hardware backends.
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
- [DHT Module](docs/dht.md)
- [Compass Module](docs/compass.md)
- [Testing Guide](docs/testing.md)
- [Building the Package](docs/building.md)

---

## Examples
See the [examples/](examples/README.md) directory for a wide range of real-world and modular usage scenarios.

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
- Adafruit_DHT
- smbus2

## License
MIT

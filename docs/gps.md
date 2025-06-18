# GPS Module Documentation

## Overview
The GPS module provides utilities for connecting to GPSD, retrieving and formatting GPS data, navigation calculations, and supporting both real and dummy backends for testing.

## Features
- Connect to GPSD or inject a custom GPS backend for testing or simulation
- Retrieve and format GPS data in APRS DMM format or decimal degrees
- Utility functions for coordinate and time formatting
- Calculate new coordinates given a bearing and distance (`get_gps_target`)
- Custom exception: `GPSError` for granular error handling
- Dependency injection for testability
- Fully modular and testable

## Usage

### Using the Real GPSD Backend
```python
from aprsrover.gps import GPS, GPSError

gps = GPS()  # Uses real gpsd if available
try:
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

### Calculating a Target Coordinate

You can calculate a new latitude and longitude given a starting point, a bearing, and a distance using `GPS.get_gps_target`:

```python
from aprsrover.gps import GPS

# Move 1km east from the equator
start_lat = 0.0
start_lon = 0.0
bearing = 90.0  # East
distance_cm = 100_000  # 1 km

target_lat, target_lon = GPS.get_gps_target(start_lat, start_lon, bearing, distance_cm)
print(f"Target coordinate: ({target_lat:.6f}, {target_lon:.6f})")
```

See [`examples/gps/sync/dummy/example_gps_target.py`](../examples/gps/sync/dummy/example_gps_target.py) for a runnable demonstration.

## Notes
- All hardware access is abstracted for easy mocking in tests.
- All public APIs use type hints and are safe for use in multi-threaded or asynchronous contexts.
- Input validation is performed for all public functions; exceptions are raised on invalid input.
- See the [examples/README.md](../examples/README.md) for more advanced usage scenarios.

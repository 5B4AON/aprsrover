# GPS Module Documentation

## Overview
The GPS module provides utilities for connecting to GPSD, retrieving and formatting GPS data, and supporting both real and dummy backends for testing.

## Features
- Connect to GPSD or inject a custom GPS backend for testing or simulation
- Retrieve and format GPS data in APRS DMM format or decimal degrees
- Utility functions for coordinate and time formatting
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

## Notes
- All hardware access is abstracted for easy mocking in tests.
- See the main README and examples for more advanced usage.

# Compass Module – Usage and Examples

The `aprsrover.compass` module provides a modular, testable interface for reading heading (magnetic north) from HMC5883L digital compass sensors. It supports both hardware and dummy backends, and offers synchronous and asynchronous APIs for flexible integration.

---

## Features

- **Hardware and Dummy Backends:**  
  Use real hardware (via smbus2) or a dummy backend for testing and development.
- **Synchronous and Asynchronous APIs:**  
  Read heading directly or monitor it in a loop using async or sync generators.
- **Safe for Import:**  
  All APIs are modular, testable, and suitable for use in other scripts or applications.
- **Custom Exceptions and Input Validation:**  
  All user input is validated; errors raise clear exceptions.

---

## Quick Start

### Hardware Backend (Synchronous)

```python
from aprsrover.compass import Compass

compass = Compass()
heading = compass.read()
print(f"Heading: {heading} degrees")
```

### Dummy Backend (Synchronous)

```python
from aprsrover.compass import Compass
from examples.dummies import DummyCompass

compass = Compass(backend=DummyCompass())
heading = compass.read()
print(f"Dummy: Heading={heading} degrees")
```

---

## Synchronous Example

See [`examples/compass/sync/dummy/basic_usage.py`](../examples/compass/sync/dummy/basic_usage.py):

```python
from aprsrover.compass import Compass
from examples.dummies import DummyCompass

compass = Compass(backend=DummyCompass())
heading = compass.read()
print(f"Dummy sync Compass: Heading={heading} degrees")
```

---

## Asynchronous Example

See [`examples/compass/async/dummy/basic_usage.py`](../examples/compass/async/dummy/basic_usage.py):

```python
import asyncio
from aprsrover.compass import Compass
from examples.dummies import DummyCompass

compass = Compass(backend=DummyCompass())

async def monitor():
    async for heading in compass.monitor_async(interval=1.0):
        print(f"Dummy async Compass: Heading={heading} degrees")
        break  # Remove this break to monitor indefinitely

asyncio.run(monitor())
```

---

## API Reference

See the docstrings in [`src/aprsrover/compass.py`](../src/aprsrover/compass.py) for full API documentation.

---

## Notes

- The hardware backend requires the `smbus2` library and a supported HMC5883L sensor connected via I2C.
- Dummy backends are safe to use on any platform and print actions to the console for testing.
- All APIs are compatible with Python 3.10+.

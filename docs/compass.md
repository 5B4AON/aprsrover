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

To interface an HMC5883L sensor with a Raspberry Pi, you'll need to enable I2C on the Raspberry Pi, connect the sensor's I2C pins (SDA, SCL, VCC, GND) to corresponding pins on the Pi, and then use a Python library to read data from the sensor.  

The HMC5883L I2C address is fixed and cannot be changed. It uses the address 0x1E.  
If you need to use multiple HMC5883L sensors, you'll need an I2C multiplexer (like a TCA9548A) to create separate I2C buses for each sensor. The multiplexer acts as an intermediary, allowing you to select which sensor to communicate with at any given time. 


1. ### Enable I2C on the Raspberry Pi:
    - Open the Raspberry Pi Configuration menu using sudo raspi-config.
    - Navigate to Interface Options -> I2C and enable it.
    - Alternatively, you can enable it by editing /boot/config.txt and adding dtparam=i2c_arm=on. 

2. ### Connect the QMC5883L to the Raspberry Pi:
    - Connect the QMC5883L's VCC (usually 3.3V or 5V) to the Raspberry Pi's 3.3V or 5V pin.
    - Connect the QMC5883L's GND to the Raspberry Pi's GND pin.
    - Connect the QMC5883L's SDA (Serial Data) to the Raspberry Pi's SDA (GPIO 2 or GPIO 3, depending on the Pi model).
    - Connect the QMC5883L's SCL (Serial Clock) to the Raspberry Pi's SCL (GPIO 2 or GPIO 3, depending on the Pi model). 

3. ### Install necessary libraries:
    - Open a terminal on your Raspberry Pi.
    - Install the smbus library: sudo apt-get install python3-smbus.

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

# DHT Module – Usage and Examples

The `aprsrover.dht` module provides a modular, testable interface for reading temperature and humidity from DHT11, DHT22, or AM2302 sensors. It supports both hardware and dummy backends, and offers synchronous and asynchronous APIs for flexible integration.

---

## Features

- **Hardware and Dummy Backends:**  
  Use real hardware (via Adafruit_DHT) or a dummy backend for testing and development.
- **Synchronous and Asynchronous APIs:**  
  Read sensor values directly or monitor them in a loop using async or sync generators.
- **Safe for Import:**  
  All APIs are modular, testable, and suitable for use in other scripts or applications.
- **Custom Exceptions and Input Validation:**  
  All user input is validated; errors raise clear exceptions.

---

## Quick Start

### Hardware Backend (Synchronous)

```python
from aprsrover.dht import DHT

dht = DHT(sensor_type='DHT22', pin=4)
temp, humidity = dht.read()
print(f"Temp: {temp} C, Humidity: {humidity} %")
```

---

## Dummy Backend Synchronous Example

See [`examples/dht/sync/dummy/basic_usage.py`](../examples/dht/sync/dummy/basic_usage.py):

```python
from aprsrover.dht import DHT
from examples.dummies import DummyDHT

dht = DHT(sensor_type='DHT22', pin=4, backend=DummyDHT())
temp, humidity = dht.read()
print(f"Dummy sync DHT: Temp={temp} C, Humidity={humidity} %")
```

---

## Dummy Backend Asynchronous Example

See [`examples/dht/async/dummy/basic_usage.py`](../examples/dht/async/dummy/basic_usage.py):

```python
import asyncio
from examples.dummies import DummyDHT
from aprsrover.dht import DHT

dht = DHT(sensor_type='DHT22', pin=4, backend=DummyDHT())

async def monitor():
    async for temp, humidity in dht.monitor_async(interval=1.0):
        print(f"Dummy async DHT: Temp={temp} C, Humidity={humidity} %")
        break  # Remove this break to monitor indefinitely

asyncio.run(monitor())
```

---

## API Reference

See the docstrings in [`src/aprsrover/dht.py`](../src/aprsrover/dht.py) for full API documentation.

---

## Notes

- The hardware backend requires the `Adafruit_DHT` library and a supported sensor connected to a GPIO pin.
- Dummy backends are safe to use on any platform and print actions to the console for testing.
- All APIs are compatible with Python 3.10+.

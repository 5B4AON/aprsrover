# UltraSonic Module

The `ultra` module provides a modular, testable interface for reading values from an ultrasonic distance sensor (e.g., HC-SR04) on a Raspberry Pi or with a dummy backend for testing.

## Features

- Synchronous and asynchronous distance measurement.
- Observer pattern for distance update notifications.
- Thread-safe operations.
- Custom exception handling.
- Dependency injection for GPIO interface (real or dummy).
- Raspberry Pi auto-detection for hardware integration.
- Suitable for use in multi-threaded or async applications.

## Usage

### Synchronous Example

```python
from aprsrover.ultra import UltraSonic, UltraSonicEvent
from examples.dummies.ultra import DummyUltra

def on_distance(event: UltraSonicEvent):
    print(f"Distance: {event.distance_cm:.1f} cm")

dummy_gpio = DummyUltra()
dummy_gpio.set_distance(42.0)
ultra = UltraSonic(trigger_pin=23, echo_pin=24, gpio=dummy_gpio)
ultra.add_observer(on_distance)
dist = ultra.measure_distance()
print(f"Measured: {dist:.1f} cm")
```

### Asynchronous Example

```python
import asyncio
from aprsrover.ultra import UltraSonic, UltraSonicEvent
from examples.dummies.ultra import DummyUltra

def on_distance(event: UltraSonicEvent):
    print(f"Distance: {event.distance_cm:.1f} cm")

dummy_gpio = DummyUltra()
dummy_gpio.set_distance(99.9)
ultra = UltraSonic(trigger_pin=23, echo_pin=24, gpio=dummy_gpio)
ultra.add_observer(on_distance)

async def main():
    dist = await ultra.measure_distance_async()
    print(f"Measured (async): {dist:.1f} cm")
    ultra.start_monitoring_async(interval=0.5)
    await asyncio.sleep(2)
    ultra.stop_monitoring_async()

asyncio.run(main())
```

---

For more details, see the module and class docstrings.
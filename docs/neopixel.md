# NeoPixel Module – Usage and Examples

The `aprsrover.neopixel` module provides a modular, testable interface for controlling NeoPixel (WS2812/WS2812B) LED strips and rings. It supports both hardware and dummy backends, and offers synchronous and asynchronous APIs for flexible integration.

---

## ⚠️ Very Important Note

**The `rpi_ws281x` library (used for real NeoPixel hardware control) requires root permissions to access the necessary hardware interfaces on a Raspberry Pi.  
All examples using the hardware backend must be run with `sudo` (e.g., `sudo python3 ...`) when running on a real Raspberry Pi.  
If you do not use `sudo`, the library will fail to initialize the hardware and your LEDs will not work.**

Dummy backend examples do **not** require root and are safe to run as a normal user.

---

## Features

- **Hardware and Dummy Backends:**  
  Use real hardware (via `AdafruitNeoPixelBackend`) or a dummy backend for testing and development.
- **Synchronous and Asynchronous APIs:**  
  Control pixels directly or animate them using async callbacks and the `NeoPixelAnimator`.
- **Safe for Import:**  
  All APIs are modular, testable, and suitable for use in other scripts or applications.
- **Custom Exceptions and Input Validation:**  
  All user input is validated; errors raise clear exceptions.

---

## Quick Start

### Hardware Backend (Synchronous)

```python
from aprsrover.neopixel import NeoPixelController

strip = NeoPixelController(num_pixels=8, pin=12)
strip.set_color((255, 0, 0))  # Set all pixels to red
strip.show()
# Run with: sudo python3 your_script.py
```

### Dummy Backend (Synchronous)

```python
from examples.dummies.neopixel import DummyNeoPixelBackend

strip = DummyNeoPixelBackend(num_pixels=8)
strip.set_color((0, 255, 0))  # Set all pixels to green
strip.show()
```

---

## Synchronous Examples

### Set All Pixels to a Color

```python
from aprsrover.neopixel import NeoPixelController

strip = NeoPixelController(num_pixels=8, pin=12)
strip.set_color((0, 0, 255))  # Blue
strip.show()
# Run with: sudo python3 your_script.py
```

### Cycle Each Pixel

```python
import time
from aprsrover.neopixel import NeoPixelController

strip = NeoPixelController(num_pixels=8, pin=12)
for i in range(8):
    strip.clear()
    strip.set_pixel(i, (255, 255, 0))  # Yellow
    strip.show()
    time.sleep(0.2)
strip.clear()
strip.show()
# Run with: sudo python3 your_script.py
```

---

## Asynchronous Examples

### Animate All Pixels Alternating Red/Blue

```python
import time
from aprsrover.neopixel import NeoPixelController, NeoPixelAnimator

strip = NeoPixelController(num_pixels=8, pin=12)
animator = NeoPixelAnimator()

async def red_blue_loop():
    if not hasattr(red_blue_loop, "state"):
        red_blue_loop.state = False
    color = (255, 0, 0) if red_blue_loop.state else (0, 0, 255)
    strip.set_color(color)
    strip.show()
    red_blue_loop.state = not red_blue_loop.state

animator.register(red_blue_loop, interval=0.2)
animator.start()
time.sleep(3)  # Animation runs in background
animator.stop()
# Run with: sudo python3 your_script.py
```

---

## Dummy Backend Examples

### Synchronous Dummy Example

```python
from examples.dummies.neopixel import DummyNeoPixelBackend

strip = DummyNeoPixelBackend(num_pixels=8)
strip.set_color((255, 0, 0))
strip.show()
```

### Asynchronous Dummy Example

```python
import time
from examples.dummies.neopixel import DummyNeoPixelBackend
from aprsrover.neopixel import NeoPixelAnimator

strip = DummyNeoPixelBackend(num_pixels=8)
animator = NeoPixelAnimator()

async def red_blue_loop():
    if not hasattr(red_blue_loop, "state"):
        red_blue_loop.state = False
    color = (255, 0, 0) if red_blue_loop.state else (0, 0, 255)
    strip.set_color(color)
    strip.show()
    red_blue_loop.state = not red_blue_loop.state

animator.register(red_blue_loop, interval=0.2)
animator.start()
time.sleep(2)
animator.stop()
```

---

## API Reference

### NeoPixelController

- `set_color(color: Tuple[int, int, int])`  
  Set all pixels to the specified RGB color.
- `set_pixel(idx: int, color: Tuple[int, int, int])`  
  Set a single pixel to the specified RGB color.
- `clear()`  
  Turn off all pixels (set to black).
- `show()`  
  Update the physical LEDs to reflect any changes.
- `set_brightness(brightness: float)`  
  Set the brightness for all pixels (0.0 to 1.0).

### NeoPixelAnimator

- `register(callback: Callable[[], Awaitable[None]], interval: float)`  
  Register an async callback to run in a loop at the given interval (seconds).
- `start()`  
  Start the animation loop in a background thread.
- `stop()`  
  Stop the animation loop and background thread.
- `unregister()`  
  Unregister the current callback.

---

## Notes

- The dummy backend prints all actions to the console and is safe for use in any environment.
- The hardware backend requires a Raspberry Pi and the `rpi_ws281x` library.
- **You must run all hardware backend examples with `sudo` on a Raspberry Pi.**
- All APIs are modular and testable; see the `tests/` directory for unit tests.

---

## See Also

- [tracks.md](./tracks.md) – Track movement and turning
- [servo.md](./servo.md) – Servo control
- [README.md](../README.md)
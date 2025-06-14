"""
neopixel.py - NeoPixel LED control utilities

This module provides the NeoPixelController class for controlling NeoPixel (WS2812/WS2812B) LED strips
or rings using a backend interface. It supports dummy/mock backends for testing and a hardware backend
using Adafruit_NeoPixel (rpi_ws281x) for real hardware.

Features:
- Set color for all or individual LEDs
- Turn off all LEDs
- Brightness control
- Modular, testable, and suitable for import/use in other scripts or applications
- Hardware access is abstracted for easy mocking in tests

Requirements:
- Python 3.10+
- rpi_ws281x (Adafruit_NeoPixel)

Usage example:
    from aprsrover.neopixel import NeoPixelController, NeoPixelAnimator
    import asyncio

    strip = NeoPixelController(num_pixels=8, pin=12)

    # Animate all pixels alternating between red and blue every 200ms
    async def red_blue_loop():
        if not hasattr(red_blue_loop, "state"):
            red_blue_loop.state = False
        color = (255, 0, 0) if red_blue_loop.state else (0, 0, 255)
        strip.set_color(color)
        strip.show()
        red_blue_loop.state = not red_blue_loop.state

    animator = NeoPixelAnimator()
    animator.register(red_blue_loop, interval=0.2)
    animator.start()

    # ... do other work here ...
    # To stop the animation:
    # animator.stop()
    # animator.unregister()

    # For testing (dummy backend)
    from aprsrover.neopixel import DummyNeoPixelBackend
    dummy = DummyNeoPixelBackend(num_pixels=8)
    strip = NeoPixelController(num_pixels=8, pin=12, backend=dummy)
    strip.set_color((0, 255, 0))
    strip.show()
"""

import asyncio
import threading
from typing import Awaitable, Callable, Optional, Tuple, Protocol, runtime_checkable, List


@runtime_checkable
class NeoPixelBackend(Protocol):
    """Interface for NeoPixel backends."""

    def set_color(self, color: Tuple[int, int, int]) -> None:
        ...

    def set_pixel(self, idx: int, color: Tuple[int, int, int]) -> None:
        ...

    def clear(self) -> None:
        ...

    def show(self) -> None:
        ...

    def set_brightness(self, brightness: float) -> None:
        ...


class DummyNeoPixelBackend:
    """
    Dummy backend for NeoPixelController, for testing and development.

    Args:
        num_pixels: Number of LEDs in the strip/ring.

    All methods are no-ops or store state in memory.
    """

    def __init__(self, num_pixels: int) -> None:
        self.num_pixels = num_pixels
        self.pixels: List[Tuple[int, int, int]] = [(0, 0, 0)] * num_pixels
        self.brightness: float = 1.0

    def set_color(self, color: Tuple[int, int, int]) -> None:
        self.pixels = [color] * self.num_pixels

    def set_pixel(self, idx: int, color: Tuple[int, int, int]) -> None:
        if not (0 <= idx < self.num_pixels):
            raise IndexError("Pixel index out of range")
        self.pixels[idx] = color

    def clear(self) -> None:
        self.set_color((0, 0, 0))

    def show(self) -> None:
        pass  # No-op for dummy

    def set_brightness(self, brightness: float) -> None:
        if not (0.0 <= brightness <= 1.0):
            raise ValueError("Brightness must be between 0.0 and 1.0")
        self.brightness = brightness


class AdafruitNeoPixelBackend:
    """
    Hardware backend for NeoPixelController using Adafruit_NeoPixel (rpi_ws281x).

    Args:
        num_pixels: Number of LEDs in the strip/ring.
        pin: GPIO pin number used for data signal (e.g., 12 for GPIO12).
        brightness: Brightness (0.0 to 1.0).
        freq_hz: LED signal frequency in hertz (default: 800_000).
        dma: DMA channel to use for generating signal (default: 10).
        invert: True to invert the signal (default: False).
        channel: PWM channel (default: 0).

    Raises:
        ImportError: If rpi_ws281x is not available.
    """

    def __init__(
        self,
        num_pixels: int,
        pin: int,
        brightness: float = 1.0,
        freq_hz: int = 800_000,
        dma: int = 10,
        invert: bool = False,
        channel: int = 0,
    ) -> None:
        try:
            from rpi_ws281x import Adafruit_NeoPixel, Color
        except ImportError as e:
            raise ImportError(
                "Adafruit_NeoPixel (rpi_ws281x) is required for hardware NeoPixel control."
            ) from e

        self.num_pixels = num_pixels
        self.pin = pin
        self.freq_hz = freq_hz
        self.dma = dma
        self.invert = invert
        self.channel = channel
        self._brightness = brightness
        self._Color = Color

        # Convert brightness (0.0-1.0) to 0-255
        led_brightness = int(max(0, min(255, round(brightness * 255))))
        self.strip = Adafruit_NeoPixel(
            num_pixels,
            pin,
            freq_hz,
            dma,
            invert,
            led_brightness,
            channel,
        )
        self.strip.begin()

    def set_color(self, color: Tuple[int, int, int]) -> None:
        """Set all pixels to the specified RGB color."""
        c = self._Color(*color)
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, c)
        self.strip.show()

    def set_pixel(self, idx: int, color: Tuple[int, int, int]) -> None:
        """Set a single pixel to the specified RGB color."""
        if not (0 <= idx < self.strip.numPixels()):
            raise IndexError("Pixel index out of range")
        c = self._Color(*color)
        self.strip.setPixelColor(idx, c)
        self.strip.show()

    def clear(self) -> None:
        """Turn off all pixels (set to black)."""
        self.set_color((0, 0, 0))

    def show(self) -> None:
        """Update the physical LEDs to reflect any changes."""
        self.strip.show()

    def set_brightness(self, brightness: float) -> None:
        """Set the brightness for all pixels."""
        if not (0.0 <= brightness <= 1.0):
            raise ValueError("Brightness must be between 0.0 and 1.0")
        # rpi_ws281x only supports brightness at construction time
        # To change at runtime, must reconstruct the strip
        if brightness != self._brightness:
            self.__init__(
                self.num_pixels,
                self.pin,
                brightness,
                self.freq_hz,
                self.dma,
                self.invert,
                self.channel,
            )


class NeoPixelController:
    """
    Controls a NeoPixel (WS2812/WS2812B) LED strip or ring using a backend.

    Args:
        num_pixels: Number of LEDs in the strip/ring.
        pin: GPIO pin number used for data signal (e.g., 12 for GPIO12).
        brightness: Brightness (0.0 to 1.0).
        backend: Optional NeoPixelBackend instance. If not provided, selects hardware backend if possible,
                 otherwise uses DummyNeoPixelBackend.

    Raises:
        ImportError: If no compatible NeoPixel library is available and no backend is provided.

    Usage example:
        strip = NeoPixelController(num_pixels=8, pin=12)
        strip.set_color((0, 0, 255))
        strip.show()
    """

    def __init__(
        self,
        num_pixels: int,
        pin: int,
        brightness: float = 1.0,
        backend: Optional[NeoPixelBackend] = None,
    ) -> None:
        self.num_pixels = num_pixels
        self.pin = pin
        self.brightness = brightness

        if backend is not None:
            self._backend = backend
        else:
            try:
                self._backend = AdafruitNeoPixelBackend(
                    num_pixels=num_pixels,
                    pin=pin,
                    brightness=brightness,
                )
            except ImportError:
                self._backend = DummyNeoPixelBackend(num_pixels=num_pixels)

    def set_color(self, color: Tuple[int, int, int]) -> None:
        """Set all pixels to the specified RGB color."""
        self._backend.set_color(color)

    def set_pixel(self, idx: int, color: Tuple[int, int, int]) -> None:
        """Set a single pixel to the specified RGB color."""
        self._backend.set_pixel(idx, color)

    def clear(self) -> None:
        """Turn off all pixels (set to black)."""
        self._backend.clear()

    def show(self) -> None:
        """Update the physical LEDs to reflect any changes."""
        self._backend.show()

    def set_brightness(self, brightness: float) -> None:
        """Set the brightness for all pixels."""
        self._backend.set_brightness(brightness)


class NeoPixelAnimator:
    """
    Manages async pixel animation callbacks in a background thread.

    Usage:
        animator = NeoPixelAnimator()
        animator.register(my_async_animation, interval=0.1)
        animator.start()
        # ... later ...
        animator.stop()
        animator.unregister()
    """

    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._task: Optional[asyncio.Task] = None
        self._callback: Optional[Callable[[], Awaitable[None]]] = None
        self._interval: float = 1.0
        self._running = threading.Event()

    def register(
        self, callback: Callable[[], Awaitable[None]], interval: float = 1.0
    ) -> None:
        """
        Register an async callback to run in a loop at the given interval (seconds).
        """
        self._callback = callback
        self._interval = interval

    def unregister(self) -> None:
        """Unregister the current callback."""
        self.stop()
        self._callback = None

    def start(self) -> None:
        """Start the animation loop in a background thread."""
        if self._thread and self._thread.is_alive():
            return  # Already running
        self._running.set()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the animation loop and background thread."""
        self._running.clear()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._cancel_task)
        if self._thread:
            self._thread.join(timeout=2)
        self._loop = None
        self._thread = None

    def _cancel_task(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._task = self._loop.create_task(self._main())
        try:
            self._loop.run_until_complete(self._task)
        except asyncio.CancelledError:
            pass

    async def _main(self) -> None:
        while self._running.is_set() and self._callback:
            await self._callback()
            await asyncio.sleep(self._interval)


from typing import List, Tuple
from aprsrover.neopixel import NeoPixelBackend


class DummyNeoPixelBackend(NeoPixelBackend):
    """
    Dummy backend for NeoPixelController, for testing and development.

    Args:
        num_pixels: Number of LEDs in the strip/ring.

    All methods are no-ops or store state in memory, but print actions to the console.
    """

    def __init__(self, num_pixels: int) -> None:
        self.num_pixels: int = num_pixels
        self.pixels: List[Tuple[int, int, int]] = [(0, 0, 0)] * num_pixels
        self.brightness: float = 1.0

    def set_color(self, color: Tuple[int, int, int]) -> None:
        self.pixels = [color] * self.num_pixels
        print(f"All pixels set to color {color}.")

    def set_pixel(self, idx: int, color: Tuple[int, int, int]) -> None:
        if not (0 <= idx < self.num_pixels):
            raise IndexError("Pixel index out of range")
        self.pixels[idx] = color
        print(f"Pixel {idx} set to color {color}.")

    def clear(self) -> None:
        self.set_color((0, 0, 0))
        print("All pixels cleared (set to black).")

    def show(self) -> None:
        print(f"Show called. Current pixel state: {self.pixels}")

    def set_brightness(self, brightness: float) -> None:
        if not (0.0 <= brightness <= 1.0):
            raise ValueError("Brightness must be between 0.0 and 1.0")
        self.brightness = brightness
        print(f"Brightness set to {brightness}.")
"""
Basic synchronous NeoPixel usage example (dummy backend).

This example sets all pixels to red, then cycles through green and blue,
and finally lights each pixel yellow one at a time.

Uses: DummyNeoPixelBackend from examples.dummies.neopixel (no hardware required).
"""

import time
from examples.dummies import DummyNeoPixelBackend

def main() -> None:
    num_pixels = 8
    backend = DummyNeoPixelBackend(num_pixels)
    # Simulate NeoPixelController API
    strip = backend

    # Set all to red
    print("Setting all pixels to red...")
    strip.set_color((255, 0, 0))
    strip.show()
    time.sleep(1)

    # Set all to green
    print("Setting all pixels to green...")
    strip.set_color((0, 255, 0))
    strip.show()
    time.sleep(1)

    # Set all to blue
    print("Setting all pixels to blue...")
    strip.set_color((0, 0, 255))
    strip.show()
    time.sleep(1)

    # Cycle each pixel yellow
    print("Cycling each pixel to yellow...")
    for i in range(num_pixels):
        strip.clear()
        strip.set_pixel(i, (255, 255, 0))
        strip.show()
        print(f"Pixel {i} set to yellow.")
        time.sleep(0.2)

    strip.clear()
    strip.show()
    print("All pixels cleared.")

if __name__ == "__main__":
    main()
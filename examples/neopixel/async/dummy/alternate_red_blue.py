"""
Asynchronous NeoPixel animation example using NeoPixelAnimator (dummy backend).

This example alternates all pixels between red and blue every 200ms
using an async callback registered with NeoPixelAnimator.

Uses: DummyNeoPixelBackend from examples.dummies.neopixel (no hardware required).
"""

import time
from examples.dummies import DummyNeoPixelBackend
from aprsrover.neopixel import NeoPixelAnimator

def main() -> None:
    num_pixels = 8
    backend = DummyNeoPixelBackend(num_pixels)
    strip = backend
    animator = NeoPixelAnimator()

    async def red_blue_loop():
        if not hasattr(red_blue_loop, "state"):
            red_blue_loop.state = False
        color = (255, 0, 0) if red_blue_loop.state else (0, 0, 255)
        print(f"All pixels changing to {color}.")
        strip.set_color(color)
        strip.show()
        red_blue_loop.state = not red_blue_loop.state

    animator.register(red_blue_loop, interval=0.2)
    print("Starting red/blue animation for 3 seconds...")
    animator.start()
    time.sleep(3)
    print("Stopping animation.")
    animator.stop()

if __name__ == "__main__":
    main()
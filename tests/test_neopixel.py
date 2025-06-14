import unittest
import time
import threading
from typing import Awaitable
from aprsrover.neopixel import (
    NeoPixelController,
    DummyNeoPixelBackend,
    AdafruitNeoPixelBackend,
    NeoPixelAnimator,
)

class TestDummyNeoPixelBackend(unittest.TestCase):
    def setUp(self) -> None:
        self.num_pixels = 5
        self.backend = DummyNeoPixelBackend(self.num_pixels)

    def test_set_color(self):
        self.backend.set_color((10, 20, 30))
        self.assertTrue(all(pixel == (10, 20, 30) for pixel in self.backend.pixels))

    def test_set_pixel(self):
        self.backend.set_color((0, 0, 0))
        self.backend.set_pixel(2, (100, 150, 200))
        self.assertEqual(self.backend.pixels[2], (100, 150, 200))
        # Out of range
        with self.assertRaises(IndexError):
            self.backend.set_pixel(-1, (1, 2, 3))
        with self.assertRaises(IndexError):
            self.backend.set_pixel(self.num_pixels, (1, 2, 3))

    def test_clear(self):
        self.backend.set_color((1, 2, 3))
        self.backend.clear()
        self.assertTrue(all(pixel == (0, 0, 0) for pixel in self.backend.pixels))

    def test_show(self):
        # Should not raise or do anything
        self.backend.show()

    def test_set_brightness(self):
        self.backend.set_brightness(0.5)
        self.assertEqual(self.backend.brightness, 0.5)
        with self.assertRaises(ValueError):
            self.backend.set_brightness(-0.1)
        with self.assertRaises(ValueError):
            self.backend.set_brightness(1.1)

class TestNeoPixelControllerWithDummy(unittest.TestCase):
    def setUp(self) -> None:
        self.num_pixels = 4
        self.backend = DummyNeoPixelBackend(self.num_pixels)
        self.controller = NeoPixelController(
            num_pixels=self.num_pixels, pin=12, backend=self.backend
        )

    def test_set_color(self):
        self.controller.set_color((11, 22, 33))
        self.assertTrue(all(pixel == (11, 22, 33) for pixel in self.backend.pixels))

    def test_set_pixel(self):
        self.controller.set_color((0, 0, 0))
        self.controller.set_pixel(1, (44, 55, 66))
        self.assertEqual(self.backend.pixels[1], (44, 55, 66))

    def test_clear(self):
        self.controller.set_color((1, 2, 3))
        self.controller.clear()
        self.assertTrue(all(pixel == (0, 0, 0) for pixel in self.backend.pixels))

    def test_show(self):
        # Should not raise or do anything
        self.controller.show()

    def test_set_brightness(self):
        self.controller.set_brightness(0.8)
        self.assertEqual(self.backend.brightness, 0.8)

    def test_set_pixel_out_of_range(self):
        with self.assertRaises(IndexError):
            self.controller.set_pixel(-1, (1, 2, 3))
        with self.assertRaises(IndexError):
            self.controller.set_pixel(self.num_pixels, (1, 2, 3))

class TestAdafruitNeoPixelBackendInit(unittest.TestCase):
    def test_import_error(self):
        # Simulate ImportError by patching import
        import sys
        import builtins

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "rpi_ws281x":
                raise ImportError("Fake import error for rpi_ws281x")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            with self.assertRaises(ImportError):
                AdafruitNeoPixelBackend(num_pixels=2, pin=12)
        finally:
            builtins.__import__ = original_import

class TestNeoPixelControllerFallback(unittest.TestCase):
    def test_fallback_to_dummy(self):
        # Patch AdafruitNeoPixelBackend to always raise ImportError
        import aprsrover.neopixel as neopixel_mod

        class AlwaysFailBackend:
            def __init__(self, *a, **kw):
                raise ImportError("fail")

        orig_backend = neopixel_mod.AdafruitNeoPixelBackend
        neopixel_mod.AdafruitNeoPixelBackend = AlwaysFailBackend
        try:
            controller = NeoPixelController(num_pixels=3, pin=12)
            self.assertIsInstance(controller._backend, DummyNeoPixelBackend)
        finally:
            neopixel_mod.AdafruitNeoPixelBackend = orig_backend

class TestNeoPixelAnimator(unittest.TestCase):
    def test_animator_runs_and_stops(self):
        animator = NeoPixelAnimator()
        call_count = 0

        async def anim_cb():
            nonlocal call_count
            call_count += 1

        animator.register(anim_cb, interval=0.05)
        animator.start()
        time.sleep(0.2)
        animator.stop()
        # Should have called anim_cb several times
        self.assertGreaterEqual(call_count, 2)
        # Should be able to unregister and not call again
        call_count2 = call_count
        animator.unregister()
        time.sleep(0.1)
        self.assertEqual(call_count, call_count2)

    def test_animator_double_start_stop(self):
        animator = NeoPixelAnimator()
        call_count = 0

        async def anim_cb():
            nonlocal call_count
            call_count += 1

        animator.register(anim_cb, interval=0.01)
        animator.start()
        animator.start()  # Should be idempotent
        time.sleep(0.05)
        animator.stop()
        animator.stop()  # Should be idempotent
        self.assertGreaterEqual(call_count, 1)

    def test_animator_no_callback(self):
        animator = NeoPixelAnimator()
        # Should not raise if start/stop with no callback
        animator.start()
        time.sleep(0.05)
        animator.stop()

    def test_animator_unregister(self):
        animator = NeoPixelAnimator()
        call_count = 0

        async def anim_cb():
            nonlocal call_count
            call_count += 1

        animator.register(anim_cb, interval=0.01)
        animator.start()
        time.sleep(0.05)
        animator.unregister()
        old_count = call_count
        time.sleep(0.05)
        self.assertEqual(call_count, old_count)

if __name__ == "__main__":
    unittest.main()
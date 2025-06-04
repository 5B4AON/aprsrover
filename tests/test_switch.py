import sys
import os
import unittest
from typing import Any, Optional, List, Callable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from aprsrover.switch import Switch, SwitchError, SwitchEvent, GPIOInterface, SwitchObserver

class DummyGPIO(GPIOInterface):
    BCM = "BCM"
    IN = "IN"
    OUT = "OUT"
    PUD_UP = "PUD_UP"

    def __init__(self) -> None:
        self.mode = None
        self.pin_modes: dict[int, tuple[Any, Optional[Any]]] = {}
        self.pin_values: dict[int, int] = {}
        self.cleanup_calls: List[Optional[int]] = []
        self.output_calls: List[tuple[int, int]] = []
        self.event_detected: dict[int, Callable] = {}

    def setmode(self, mode: Any) -> None:
        self.mode = mode

    def setup(self, pin: int, mode: Any, pull_up_down: Any = None) -> None:
        self.pin_modes[pin] = (mode, pull_up_down)
        if mode == self.OUT:
            self.pin_values[pin] = 1  # Default OFF
        elif mode == self.IN:
            self.pin_values.setdefault(pin, 1)  # Default pulled up

    def input(self, pin: int) -> int:
        return self.pin_values.get(pin, 1)

    def output(self, pin: int, value: int) -> None:
        self.pin_values[pin] = value
        self.output_calls.append((pin, value))

    def cleanup(self, pin: Optional[int] = None) -> None:
        self.cleanup_calls.append(pin)

    def add_event_detect(self, pin: int, edge: Any, callback: Any, bouncetime: int = ...) -> None:
        self.event_detected[pin] = callback

    def remove_event_detect(self, pin: int) -> None:
        if pin in self.event_detected:
            del self.event_detected[pin]

class TestSwitch(unittest.TestCase):
    def setUp(self) -> None:
        self.gpio = DummyGPIO()

    def test_switch_in_setup_and_get_state(self) -> None:
        self.gpio.pin_values[2] = 0
        sw = Switch(pin=2, direction="IN", gpio=self.gpio)
        self.assertEqual(self.gpio.pin_modes[2][0], self.gpio.IN)
        self.assertTrue(sw.get_state())
        self.gpio.pin_values[2] = 1
        self.assertFalse(sw.get_state())

    def test_switch_out_setup_and_get_set_state(self) -> None:
        sw = Switch(pin=3, direction="OUT", gpio=self.gpio)
        self.assertEqual(self.gpio.pin_modes[3][0], self.gpio.OUT)
        self.assertFalse(sw.get_state())
        sw.set_state(True)
        self.assertTrue(sw.get_state())
        self.assertEqual(self.gpio.pin_values[3], 0)  # ON (active low)
        sw.set_state(False)
        self.assertFalse(sw.get_state())
        self.assertEqual(self.gpio.pin_values[3], 1)  # OFF

    def test_switch_invalid_direction_raises(self) -> None:
        class BadGPIO(DummyGPIO):
            def setup(self, pin: int, mode: Any, pull_up_down: Any = None) -> None:
                raise ValueError("direction must be 'IN' or 'OUT'")
        with self.assertRaises(SwitchError):
            Switch(pin=10, direction="BAD", gpio=BadGPIO())

    def test_set_state_on_input_raises(self) -> None:
        sw = Switch(pin=4, direction="IN", gpio=self.gpio)
        with self.assertRaises(SwitchError):
            sw.set_state(True)

    def test_set_state_exception_raises(self) -> None:
        class FailingGPIO(DummyGPIO):
            def __init__(self):
                super().__init__()
                self.fail_next = False
            def output(self, pin: int, value: int) -> None:
                if self.fail_next:
                    raise RuntimeError("fail")
                super().output(pin, value)
        gpio = FailingGPIO()
        sw = Switch(pin=5, direction="OUT", gpio=gpio)
        gpio.fail_next = True
        with self.assertRaises(SwitchError):
            sw.set_state(True)

    def test_observer_notified_on_out_state_change(self) -> None:
        sw = Switch(pin=6, direction="OUT", gpio=self.gpio)
        events: List[SwitchEvent] = []
        sw.add_observer(lambda e: events.append(e))
        sw.set_state(True)
        self.assertTrue(events[-1].state)
        sw.set_state(False)
        self.assertFalse(events[-1].state)

    def test_observer_notified_on_in_state_change(self) -> None:
        import time
        sw = Switch(pin=7, direction="IN", gpio=self.gpio, debounce_ms=5)
        events: List[SwitchEvent] = []
        sw.add_observer(lambda e: events.append(e))
        sw.start_monitoring()
        self.gpio.pin_values[7] = 0  # ON
        time.sleep(0.02)
        self.gpio.pin_values[7] = 1  # OFF
        time.sleep(0.02)
        sw.stop_monitoring()
        self.assertTrue(any(e.state is True for e in events))
        self.assertTrue(any(e.state is False for e in events))

    def test_remove_observer(self) -> None:
        sw = Switch(pin=8, direction="OUT", gpio=self.gpio)
        called: List[bool] = []
        def obs(event: SwitchEvent) -> None:
            called.append(event.state)
        sw.add_observer(obs)
        sw.set_state(True)
        sw.remove_observer(obs)
        sw.set_state(False)
        self.assertEqual(called, [True])

    def test_remove_nonexistent_observer(self) -> None:
        sw = Switch(pin=9, direction="OUT", gpio=self.gpio)
        def obs(event: SwitchEvent) -> None:
            pass
        # Should not raise
        sw.remove_observer(obs)

    def test_notify_observers_handles_exception(self) -> None:
        sw = Switch(pin=11, direction="OUT", gpio=self.gpio)
        def bad_observer(event: SwitchEvent) -> None:
            raise RuntimeError("fail")
        sw.add_observer(bad_observer)
        # Should not raise
        sw.set_state(True)

    def test_cleanup_calls_gpio_cleanup(self) -> None:
        sw = Switch(pin=12, direction="IN", gpio=self.gpio)
        sw.cleanup()
        self.assertEqual(self.gpio.cleanup_calls[-1], 12)

    def test_monitor_thread_safe_start_stop(self) -> None:
        import time
        sw = Switch(pin=13, direction="IN", gpio=self.gpio, debounce_ms=5)
        sw.start_monitoring()
        sw.start_monitoring()  # Should be safe to call twice
        time.sleep(0.01)
        sw.stop_monitoring()
        sw.stop_monitoring()  # Should be safe to call twice

    def test_add_multiple_observers(self) -> None:
        sw = Switch(pin=14, direction="OUT", gpio=self.gpio)
        called: List[bool] = []
        def obs1(event: SwitchEvent) -> None:
            called.append(event.state)
        def obs2(event: SwitchEvent) -> None:
            called.append(not event.state)
        sw.add_observer(obs1)
        sw.add_observer(obs2)
        sw.set_state(True)
        self.assertIn(True, called)
        self.assertIn(False, called)

    def test_get_state_out_reflects_internal_state(self) -> None:
        sw = Switch(pin=15, direction="OUT", gpio=self.gpio)
        self.assertFalse(sw.get_state())
        sw.set_state(True)
        self.assertTrue(sw.get_state())

    def test_get_state_in_reflects_gpio_input(self) -> None:
        sw = Switch(pin=16, direction="IN", gpio=self.gpio)
        self.gpio.pin_values[16] = 0
        self.assertTrue(sw.get_state())
        self.gpio.pin_values[16] = 1
        self.assertFalse(sw.get_state())

    def test_async_monitor_notifies_on_change(self) -> None:
        import asyncio

        sw = Switch(pin=17, direction="IN", gpio=self.gpio)
        events: List[SwitchEvent] = []
        sw.add_observer(lambda e: events.append(e))

        async def simulate():
            self.gpio.pin_values[17] = 1
            await asyncio.sleep(0.03)
            self.gpio.pin_values[17] = 0
            await asyncio.sleep(0.03)
            self.gpio.pin_values[17] = 1
            await asyncio.sleep(0.03)

        async def run_monitor():
            task = asyncio.create_task(sw.async_monitor(poll_interval=0.01))
            await simulate()
            await asyncio.sleep(0.03)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run_monitor())
        self.assertTrue(any(e.state is True for e in events))
        self.assertTrue(any(e.state is False for e in events))

if __name__ == "__main__":
    unittest.main()
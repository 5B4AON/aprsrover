"""
Synchronous example for UltraSonic using DummyUltra.

This example demonstrates:
- How to use the UltraSonic class with a dummy GPIO backend for testing.
- How to register an observer for distance measurements.
- How to take a single synchronous measurement and receive a callback.
- How to start and stop periodic monitoring of distance in a background thread.

Requires:
    - aprsrover.ultra.UltraSonic
    - examples.dummies.ultra.DummyUltra

Run this script directly to see output from both single and periodic measurements.
"""
from aprsrover.ultra import UltraSonic, UltraSonicEvent
from examples.dummies.ultra import DummyUltra
import time

def on_distance(event: UltraSonicEvent):
    print(f"[SYNC] Distance: {event.distance_cm:.1f} cm")

dummy_gpio = DummyUltra()
dummy_gpio.set_distance(42.0)
ultra = UltraSonic(trigger_pin=23, echo_pin=24, gpio=dummy_gpio)
ultra.add_observer(on_distance)

# Takes a single distance measurement and notifies observers once.
print(f"Measured: {ultra.measure_distance():.1f} cm")

# Starts a background thread that repeatedly measures distance every 0.2 seconds.
# Each time a new measurement is taken, all registered observers are notified.
ultra.start_monitoring(interval=0.2)
time.sleep(1)
ultra.stop_monitoring()
ultra.cleanup()

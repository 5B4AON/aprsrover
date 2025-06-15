"""
Asynchronous example for UltraSonic using DummyUltra.

This example demonstrates:
- How to use the UltraSonic class with a dummy GPIO backend for testing.
- How to register an observer for distance measurements.
- How to take a single asynchronous measurement and receive a callback.
- How to start and stop periodic asynchronous monitoring of distance.

Requires:
    - aprsrover.ultra.UltraSonic
    - examples.dummies.ultra.DummyUltra

Run this script directly to see output from both single and periodic async measurements.
"""
from aprsrover.ultra import UltraSonic, UltraSonicEvent
from examples.dummies import DummyUltra
import asyncio

def on_distance(event: UltraSonicEvent):
    print(f"[ASYNC] Distance: {event.distance_cm:.1f} cm")

dummy_gpio = DummyUltra()
dummy_gpio.set_distance(99.9)
ultra = UltraSonic(trigger_pin=23, echo_pin=24, gpio=dummy_gpio)
ultra.add_observer(on_distance)

async def main():
    # Takes a single async distance measurement and notifies observers once.
    measured = await ultra.measure_distance_async()
    print(f"Measured distance for 20°C: {measured:.1f} cm")
    adjusted = UltraSonic.adjust_measurement_based_on_temp(25.0, measured)
    print(f"Adjusted distance for 25°C: {adjusted:.1f} cm")
    
    # Starts an async background thread that repeatedly measures distance every 0.2 seconds.
    # Each time a new measurement is taken, all registered observers are notified.
    monitor_task = asyncio.create_task(ultra.async_monitor(interval=0.2))
    await asyncio.sleep(1)
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    ultra.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

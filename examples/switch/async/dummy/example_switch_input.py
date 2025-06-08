"""
Showcase: Use DummySwitch for input (async).

Demonstrates observing state changes for input pins using async_monitor.
"""
import asyncio
import logging
from examples.dummies import DummySwitch
from aprsrover.switch import Switch

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    gpio = DummySwitch()

    # Input switch: cannot set state directly, but can simulate input via DummySwitch API
    input_switch = Switch(pin=18, direction="IN", gpio=gpio)
    input_switch.add_observer(
        lambda event: print(f"Input pin {event.pin} is now {'ON' if event.state else 'OFF'}")
    )
    print(f"Initial input state: {input_switch.get_state()}")

    # Start async monitoring in the background
    monitor_task = asyncio.create_task(input_switch.async_monitor(poll_interval=0.05))

    # Simulate input events: LOW (ON), then HIGH (OFF)
    await asyncio.sleep(0.1)
    if hasattr(gpio, "simulate_input"):
        gpio.simulate_input(pin=18, state=False)  # LOW (ON)
        await asyncio.sleep(0.1)
        gpio.simulate_input(pin=18, state=True)   # HIGH (OFF)
        await asyncio.sleep(0.1)
    else:
        print("DummySwitch does not support input simulation.")

    # Stop after demonstration
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(main())

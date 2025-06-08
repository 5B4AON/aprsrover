"""
Showcase: Use DummySwitch for input (sync).

Demonstrates observing state changes for input pins using start_monitoring (synchronous monitoring).
"""
import logging
import time
from examples.dummies import DummySwitch
from aprsrover.switch import Switch

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    gpio = DummySwitch()

    # Input switch: cannot set state directly, but can simulate input via DummySwitch API
    input_switch = Switch(pin=18, direction="IN", gpio=gpio)
    input_switch.add_observer(
        lambda event: print(f"Input pin {event.pin} is now {'ON' if event.state else 'OFF'}")
    )
    print(f"Initial input state: {input_switch.get_state()}")

    # Start synchronous monitoring in the background
    input_switch.start_monitoring()

    # Simulate input events: LOW (ON), then HIGH (OFF)
    time.sleep(0.1)
    if hasattr(gpio, "simulate_input"):
        gpio.simulate_input(pin=18, state=False)  # LOW (ON)
        time.sleep(0.1)
        gpio.simulate_input(pin=18, state=True)   # HIGH (OFF)
        time.sleep(0.1)
    else:
        print("DummySwitch does not support input simulation.")

    # Stop after demonstration
    input_switch.stop_monitoring()

if __name__ == "__main__":
    main()
"""
Showcase: Use DummySwitch for output (sync).

Demonstrates observing state changes for output pins using synchronous state changes.

Usage example:
    python examples/switch/sync/dummy/example_switch_output.py
"""

import logging
import time
from examples.dummies import DummySwitch
from aprsrover.switch import Switch

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    gpio = DummySwitch()

    # Output switch: can set state directly
    output_switch = Switch(pin=17, direction="OUT", gpio=gpio)
    output_switch.add_observer(
        lambda event: print(f"Output pin {event.pin} is now {'ON' if event.state else 'OFF'}")
    )
    print(f"Initial output state: {output_switch.get_state()}")

    # Toggle output state: ON, then OFF
    time.sleep(0.1)
    output_switch.set_state(True)   # ON
    time.sleep(0.1)
    output_switch.set_state(False)  # OFF
    time.sleep(0.1)

if __name__ == "__main__":
    main()
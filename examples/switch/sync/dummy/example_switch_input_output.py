"""
Showcase: Use DummySwitch for input and output (sync)
"""
import logging
from examples.dummies import DummySwitch
from aprsrover.switch import Switch

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    gpio = DummySwitch()
    switch = Switch(pin=17, direction="IN", gpio=gpio)
    print(f"Switch pressed: {not bool(switch.get_state())}")
    switch_out = Switch(pin=18, direction="OUT", gpio=gpio)
    switch_out.set_state(True)
    print(f"Switch output state: {switch_out.get_state()}")

if __name__ == "__main__":
    main()

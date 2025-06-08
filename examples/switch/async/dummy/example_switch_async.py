"""
Async Example: Check switch state using the Dummy backend.
"""
import asyncio
import logging
from examples.dummies import DummyGPIO
from aprsrover.switch import Switch

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    gpio = DummyGPIO()
    switch = Switch(pin=17, direction="IN", gpio=gpio)
    print(f"Switch pressed: {not bool(switch.get_state())}")

if __name__ == "__main__":
    asyncio.run(main())

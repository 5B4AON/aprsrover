"""
Asynchronous compass monitoring example (dummy backend).

This example prints heading every second for 3 seconds using async monitoring.
Uses: DummyCompass from examples.dummies.compass (no hardware required).
"""
import asyncio
from aprsrover.compass import Compass
from examples.dummies import DummyCompass

def main() -> None:
    compass = Compass(backend=DummyCompass())

    async def monitor():
        count = 0
        async for heading in compass.monitor_async(interval=1.0):
            print(f"Dummy async Compass: Heading={heading} degrees")
            count += 1
            if count >= 3:
                break
    asyncio.run(monitor())

if __name__ == "__main__":
    main()

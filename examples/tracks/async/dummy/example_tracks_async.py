"""
Async Example: Use tracks with the Dummy backend.
"""
import asyncio
import logging
from examples.dummies import DummyPWM
from aprsrover.tracks import Tracks

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    pwm = DummyPWM()
    tracks = Tracks(pwm=pwm)
    await tracks.move_async(80, 80, 1)
    print(f"PWM calls: {pwm.calls}")

if __name__ == "__main__":
    asyncio.run(main())

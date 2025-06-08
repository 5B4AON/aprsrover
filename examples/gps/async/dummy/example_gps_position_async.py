"""
Async Example: Get GPS position using the Dummy backend.
"""
import asyncio
import logging
from examples.dummies import DummyGPSD
from aprsrover.gps import GPS

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    gps = GPS(gpsd=DummyGPSD())
    data = gps.get_gps_data_dmm()
    print(f"Current position: {data}")

if __name__ == "__main__":
    asyncio.run(main())

"""
Async Integration Example: APRS, GPS, and Tracks using Dummy backends.
"""
import asyncio
import logging
from examples.dummies import DummyAPRS, DummyGPSD, DummyPWM
from aprsrover.aprs import Aprs
from aprsrover.gps import GPS
from aprsrover.tracks import Tracks

logging.basicConfig(level=logging.DEBUG)

async def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    gps = GPS(gpsd=DummyGPSD())
    pwm = DummyPWM()
    tracks = Tracks(pwm=pwm)
    await aprs.connect()
    pos = gps.get_gps_data_dmm()
    await tracks.move_async(80, 80, 1)
    aprs.send_my_message_no_ack(
        mycall="N0CALL-1",
        path=["WIDE1-1"],
        recipient="DEST-1",
        message=f"Current position: {pos}"
    )
    print(f"Tracks PWM calls: {pwm.calls}")
    print("Integration async example complete.")

if __name__ == "__main__":
    asyncio.run(main())

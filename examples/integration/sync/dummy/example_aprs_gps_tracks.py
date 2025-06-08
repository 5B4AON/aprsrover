"""
Integration Example: APRS, GPS, and Tracks using Dummy backends (synchronous).
"""
import logging
logging.basicConfig(level=logging.DEBUG)

from examples.dummies import DummyAPRS, DummyGPSD, DummyPWM
from aprsrover.aprs import Aprs
from aprsrover.gps import GPS
from aprsrover.tracks import Tracks

def main() -> None:
    aprs = Aprs(host="localhost", port=8001, kiss=DummyAPRS())
    gps = GPS(gpsd=DummyGPSD())
    pwm = DummyPWM()
    tracks = Tracks(pwm=pwm)
    aprs.initialized = True
    pos = gps.get_gps_data_dmm()
    tracks.set_left_track_speed(50)
    tracks.set_right_track_speed(50)
    aprs.send_my_message_no_ack(
        mycall="N0CALL-1",
        path=["WIDE1-1"],
        recipient="DEST-1",
        message=f"Current position: {pos}"
    )
    print(f"Tracks PWM calls: {pwm.calls}")
    print("Integration example complete.")

if __name__ == "__main__":
    main()

"""
Example: Use tracks with the Dummy backend (synchronous).
"""
import logging
logging.basicConfig(level=logging.DEBUG)

from examples.dummies import DummyPWM
from aprsrover.tracks import Tracks

def main() -> None:
    pwm = DummyPWM()
    tracks = Tracks(pwm=pwm)
    tracks.set_left_track_speed(50)
    tracks.set_right_track_speed(-30)
    print(f"PWM calls: {pwm.calls}")

if __name__ == "__main__":
    main()

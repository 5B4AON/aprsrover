"""
Showcase: Set left and right track speeds using DummyPWM (sync)
"""
import logging
from examples.dummies import DummyPWM
from aprsrover.tracks import Tracks

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    pwm = DummyPWM()
    tracks = Tracks(pwm=pwm)
    tracks.set_left_track_speed(80)
    tracks.set_right_track_speed(-30)
    print(f"PWM calls: {pwm.calls}")

if __name__ == "__main__":
    main()

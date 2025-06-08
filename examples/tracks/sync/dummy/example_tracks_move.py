"""
Showcase: Move both tracks for a duration using DummyPWM (sync)
"""
import logging
from examples.dummies import DummyPWM
from aprsrover.tracks import Tracks

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    pwm = DummyPWM()
    tracks = Tracks(pwm=pwm)
    tracks.move(60, 60, 2.5)
    print(f"PWM calls: {pwm.calls}")

if __name__ == "__main__":
    main()

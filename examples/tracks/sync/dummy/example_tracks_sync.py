"""
Synchronous usage examples for the Tracks class using DummyPWM.
Demonstrates basic and advanced synchronous movement and turning features.
"""

from aprsrover.tracks import Tracks
from examples.dummies import DummyPWM

def main() -> None:
    tracks = Tracks(pwm=DummyPWM())

    # Move both tracks forward at 60% for 2 seconds, then stop
    print("Moving forward (sync)...")
    tracks.move(60, 60, 2)

    # Move both tracks backward at 40% for 1.5 seconds, then stop
    print("Moving backward (sync)...")
    tracks.move(-40, -40, 1.5)

    # Move left track forward, right track stopped (turn right arc)
    print("Turning right arc (sync)...")
    tracks.move(50, 0, 1.2)

    # Move with acceleration smoothing (ramps up to speed)
    print("Moving with acceleration smoothing (sync)...")
    tracks.move(80, 80, 3, accel=80, accel_interval=0.1)

    # Move without stopping at the end (tracks keep running)
    print("Moving without stopping at end (sync)...")
    tracks.move(70, 70, 2, stop_at_end=False)
    print(f"Left speed: {tracks.get_left_track_speed()}, Right speed: {tracks.get_right_track_speed()}")
    tracks.stop()
    print("Tracks stopped.")

    # Synchronous turn: spin in place 180 degrees left
    print("Spin in place 180 degrees left (sync)...")
    tracks.turn(70, 0, 'left', angle_deg=180)

    # Synchronous arc turn: arc right for 2.5 seconds
    print("Arc right for 2.5 seconds (sync)...")
    tracks.turn(60, 20, 'right', duration=2.5)

    # Synchronous arc turn with acceleration smoothing and do not stop at end
    print("Arc left 90 degrees with smoothing, do not stop at end (sync)...")
    tracks.turn(50, 30, 'left', angle_deg=90, accel=40, accel_interval=0.1, stop_at_end=False)
    tracks.stop()
    print("Tracks stopped.")

if __name__ == "__main__":
    main()

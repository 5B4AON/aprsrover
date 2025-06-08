"""
Asynchronous usage examples for the Tracks class using DummyPWM.
Demonstrates async movement, turning, acceleration smoothing, and interruption.
"""

import asyncio
from aprsrover.tracks import Tracks, TracksError

class DummyPWM:
    def set_pwm(self, channel, on, off):
        print(f"DummyPWM: set_pwm(channel={channel}, on={on}, off={off})")

async def main() -> None:
    tracks = Tracks(pwm=DummyPWM())

    # Move both tracks forward at 60% for 2 seconds, then stop
    print("Moving forward (async)...")
    await tracks.move_async(60, 60, 2)

    # Move both tracks backward at 40% for 1.5 seconds, then stop
    print("Moving backward (async)...")
    await tracks.move_async(-40, -40, 1.5)

    # Move left track forward, right track stopped (turn right arc)
    print("Turning right arc (async)...")
    await tracks.move_async(50, 0, 1.2)

    # Move with acceleration smoothing (ramps up to speed)
    print("Moving with acceleration smoothing (async)...")
    await tracks.move_async(80, 80, 3, accel=80, accel_interval=0.1)

    # Move without stopping at the end (tracks keep running)
    print("Moving without stopping at end (async)...")
    await tracks.move_async(70, 70, 2, stop_at_end=False)
    print(f"Left speed: {tracks.get_left_track_speed()}, Right speed: {tracks.get_right_track_speed()}")
    tracks.stop()
    print("Tracks stopped.")

    # Demonstrate interruption (cancel movement before completion)
    print("Demonstrating async interruption...")
    move_task = asyncio.create_task(tracks.move_async(80, 80, 10, accel=40))
    await asyncio.sleep(2)  # Simulate obstacle detection after 2 seconds
    move_task.cancel()
    try:
        await move_task
    except asyncio.CancelledError:
        print("Move interrupted!")
        print(f"Current speeds: left={tracks.get_left_track_speed()}, right={tracks.get_right_track_speed()}")
        tracks.stop()
        print("Tracks stopped after interruption.")

    # Asynchronous turn: spin in place 90 degrees left
    print("Spin in place 90 degrees left (async)...")
    await tracks.turn_async(70, 0, 'left', angle_deg=90)

    # Asynchronous arc turn with acceleration smoothing, do not stop at end
    print("Arc left 45 degrees with smoothing, do not stop at end (async)...")
    await tracks.turn_async(40, 30, 'left', angle_deg=45, accel=30, accel_interval=0.05, stop_at_end=False)
    tracks.stop()
    print("Tracks stopped.")

if __name__ == "__main__":
    asyncio.run(main())

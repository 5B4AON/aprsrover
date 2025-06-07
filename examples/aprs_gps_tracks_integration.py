"""
Example: Integrating APRS, GPS, and Tracks

This script demonstrates:
- Registering APRS observers for a specific callsign (e.g., "5B4AON-9")
- Handling incoming APRS messages to control rover tracks or report position
- Sending acknowledgements if requested
- Using GPS to report current position as an APRS object
- Using decimal coordinates for calculations and DMM/DHM for APRS transmission

Requirements:
    - KISS TNC accessible (e.g., Direwolf running in KISS mode)
    - gpsd running and accessible
    - Adafruit PCA9685 PWM controller connected

Run this script from the project root:
    python examples/aprs_gps_tracks_integration.py
"""

from aprsrover.aprs import Aprs, AprsError
from aprsrover.gps import GPS, GPSError
from aprsrover.tracks import Tracks, TracksError
import asyncio
from ax253 import Frame

CALLSIGN = "5B4AON-9"
APRS_PATH = ["WIDE1-1"]

aprs = Aprs(host="localhost", port=8001)
gps = GPS()
tracks = Tracks()


def move_callback(frame: Frame) -> None:
    """
    Callback for movement commands.
    Expects message like:
      'Mv 50 -50 2.5 70 70 3'
    Each group of three numbers is (left_speed, right_speed, duration).
    - Total duration for all movements must not exceed 30 seconds.
    - Individual duration for any movement must not exceed 10 seconds.
    - Ignore incomplete groups.
    """
    msg = Aprs.get_my_message(CALLSIGN, frame)
    if not msg or not msg.startswith("Mv "):
        return
    aprs.send_ack_if_requested(frame, CALLSIGN, APRS_PATH)
    try:
        parts = msg[3:].strip().split()
        # Only process complete groups of 3
        movements = []
        for i in range(0, len(parts) - 2, 3):
            try:
                left_speed = float(parts[i])
                right_speed = float(parts[i + 1])
                duration = float(parts[i + 2])
                if duration <= 0 or duration > 10:
                    print(f"Ignoring movement with invalid duration: {duration}")
                    continue
                movements.append((left_speed, right_speed, duration))
            except ValueError:
                print(f"Ignoring invalid movement group: {parts[i:i+3]}")
                continue

        total_duration = sum(d for _, _, d in movements)
        if total_duration > 30:
            print(f"Total duration {total_duration} exceeds 30 seconds. Movements will be truncated.")
            # Truncate movements to not exceed 30 seconds
            truncated = []
            running_total = 0.0
            for left, right, dur in movements:
                if running_total + dur > 30:
                    dur = 30 - running_total
                    if dur > 0:
                        truncated.append((left, right, dur))
                    break
                truncated.append((left, right, dur))
                running_total += dur
            movements = truncated

        for left_speed, right_speed, duration in movements:
            print(f"Moving left track at {left_speed}, right track at {right_speed} for {duration} seconds.")
            tracks.move(left_speed, right_speed, duration)
    except TracksError as te:
        print(f"Tracks error: {te}")
    except Exception as e:
        print(f"Move callback error: {e}")

def pos_callback(frame: Frame) -> None:
    """
    Callback for position requests.
    Expects message 'Pos', responds with an APRS object containing current position.
    """
    msg = Aprs.get_my_message(CALLSIGN, frame)
    if msg != "Pos":
        return
    aprs.send_ack_if_requested(frame, CALLSIGN)
    try:
        gps_data = gps.get_gps_data_dmm()
        if gps_data is None:
            print("Failed to retrieve GPS data for position report.")
            return
        lat, lon, tm, _ = gps_data
        print(f"Sending position object: {lat}, {lon}, {tm}")
        aprs.send_object_report(
            mycall=CALLSIGN,
            path=APRS_PATH,
            time_dhm=tm,
            lat_dmm=lat,
            long_dmm=lon,
            symbol_id="/",
            symbol_code="O",
            comment="here I am"
        )
    except (GPSError, AprsError) as e:
        print(f"Position callback error: {e}")

async def main() -> None:
    try:
        await aprs.connect()
        aprs.register_observer(CALLSIGN, move_callback)
        aprs.register_observer(CALLSIGN, pos_callback)
        print(f"APRS observer registered for {CALLSIGN}. Waiting for messages (Ctrl+C to exit)...")
        while True:
            await asyncio.sleep(1)
    except AprsError as ae:
        print(f"APRS error: {ae}")

if __name__ == "__main__":
    asyncio.run(main())
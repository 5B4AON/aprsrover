"""
Example: Integrating APRS, GPS, and Tracks

This script demonstrates:
- Registering APRS observers for a specific callsign (e.g., "5B4AON-9")
- Handling incoming APRS messages to control rover tracks or report position
- Sending acknowledgements if requested
- Using GPS to report current position as an APRS object

Requirements:
    - KISS TNC accessible (e.g., Direwolf running in KISS mode)
    - gpsd running and accessible
    - Adafruit PCA9685 PWM controller connected

Run this script from the project root:
    python examples/aprs_gps_tracks_integration.py
"""

import asyncio
from aprsrover.aprs import Aprs, AprsError
from aprsrover.gps import GPS, GPSError
from aprsrover.tracks import Tracks, TracksError, PWMControllerInterface
from aprsrover.hw_info import HWInfo, HWInfoError, HWInfoInterface
from ax253 import Frame
import logging
from examples.dummies import DummyGPS
from examples.dummies import DummyPWM
from examples.dummies import DummyHWInfo

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


CALLSIGN = "5B4AON-9"
APRS_PATH = ["WIDE1-1"]

aprs = Aprs(host="localhost", port=8002)
gps = DummyGPS()

dummy_pwm = DummyPWM()
tracks = Tracks(pwm=dummy_pwm)
#tracks = Tracks()

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
    #print("move_callback:", msg)
    if not msg or not msg.startswith("Mv "):
        return
    # Only send ack if the message matches the search condition
    aprs.send_ack_if_requested(frame, CALLSIGN, APRS_PATH)
    try:
        parts = msg[3:].strip().split()
        # Only process complete groups of 3
        movements = []
        for i in range(0, len(parts) - 2, 3):
            try:
                left_speed = int(parts[i])
                right_speed = int(parts[i + 1])
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
            #print(f"Moving left track at {left_speed}, right track at {right_speed} for {duration} seconds.")
            tracks.move(left_speed, right_speed, duration, 100, stop_at_end=False)
        tracks.move(0, 0, 1, 100)
    except TracksError as te:
        print(f"Tracks error: {te}")
    except Exception as e:
        print(f"Move callback error: {e}")

def pos_callback(frame: Frame):
    """
    Callback for position requests.
    Expects message '?APRSS', responds with an APRS position message with a timestamp.
    """
    msg = Aprs.get_my_message(CALLSIGN, frame).strip()
    #print("pos_callback:", msg)
    if msg != "?APRSP":
        return
    # Only send ack if the message matches the search condition
    aprs.send_ack_if_requested(frame, CALLSIGN, APRS_PATH)
    try:
        # APRS DMM: 3509.57N, 03318.59E, 011500z, 0
        gps_data = gps.get_position()
        if gps_data is None:
            print("Failed to retrieve GPS data for position report.")
            return
        lat, lon, tm, _ = gps_data
        print(f"Sending position object: {lat}, {lon}, {tm}")
        aprs.send_position_report(
            mycall=CALLSIGN,
            path=APRS_PATH,
            time_dhm=tm,
            lat_dmm=lat,
            long_dmm=lon,
            symbol_id="/",
            symbol_code=">",
            comment="ROVER",
        )
    except (GPSError, AprsError) as e:
        print(f"Position callback error: {e}")



def status_callback(frame: Frame):
    """
    Callback for status requests.
    Expects message '?APRSS', responds with an APRS status message.
    """
    msg = Aprs.get_my_message(CALLSIGN, frame).strip()
    #print("pos_callback:", msg)
    if msg != "?APRSS":
        return
    # Only send ack if the message matches the search condition
    aprs.send_ack_if_requested(frame, CALLSIGN, APRS_PATH)
    try:
        gps_data = gps.get_position()
        if gps_data is None:
            print("Failed to retrieve GPS data for position report.")
            return
        lat, lon, tm, _ = gps_data
        hw = HWInfo(backend=DummyHWInfo())  # Uses dummy hardware info
        cpu_temp = hw.get_cpu_temp() + "°C"  # e.g., "48.2°C"
        cpu_use = hw.get_cpu_usage() + "%"  # e.g., "12.5%"
        ram_use = hw.get_ram_usage() + "%"  # e.g., "42.0%"
        # Format uptime as 01h 23m 45s
        h, m, s = hw.get_uptime().split(":")
        uptime = f"{h}h {m}m {s}s"  # e.g., "01h 23m 45s"
        print(f"Sending status")
        aprs.send_status_report(
            mycall=CALLSIGN,
            path=APRS_PATH,
            time_dhm=tm,
            status=f"UP: {uptime}, CPU: {cpu_use} {cpu_temp}, RAM: {ram_use}",
        )
    except (GPSError, AprsError) as e:
        print(f"Status callback error: {e}")


async def main() -> None:
    try:
        await aprs.connect()
        #gps.connect()
        aprs.register_observer(CALLSIGN, move_callback)
        aprs.register_observer(CALLSIGN, pos_callback)
        aprs.register_observer(CALLSIGN, status_callback)
        print(f"APRS observer registered for {CALLSIGN}. Waiting for messages (Ctrl+C to exit)...")
        await aprs.run()
    except AprsError as ae:
        print(f"APRS error: {ae}")

if __name__ == "__main__":
    asyncio.run(main())

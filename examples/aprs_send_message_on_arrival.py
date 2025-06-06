"""
Example: Send APRS message when rover arrives at a destination

This script polls the current GPS position every 10 seconds and, when the rover is within
20 meters of the provided destination coordinates, sends an APRS message from 5B4AON-9
to 5B4AON-7 with the message "Arrived at destination". It also sends a final APRS object
report at arrival, and every 5 minutes, if the rover has moved more than 20 meters from
its last reported position, it sends an object report with the current position.

- Uses decimal coordinates for accurate distance checking.
- Uses DMM and DHM formats only when sending APRS messages/objects.
- Designed for integration with KISS TNC and gpsd.

Requirements:
    - KISS TNC accessible (e.g., Direwolf running in KISS mode)
    - gpsd running and accessible

Run this script from the project root:
    python examples/aprs_send_message_on_arrival.py
"""

import time
import math
from aprsrover.aprs import Aprs, AprsError
from aprsrover.gps import GPS, GPSError
import asyncio

CALLSIGN_FROM = "5B4AON-9"
CALLSIGN_TO = "5B4AON-7"
APRS_PATH = ["WIDE1-1"]

# Set your destination coordinates here (decimal degrees)
DEST_LAT = 35.123456
DEST_LON = 33.123456

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth (meters).
    """
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def main() -> None:
    """
    Polls the current GPS position every 10 seconds. When the rover is within 20 meters of the
    destination, sends an APRS message and a final object report. Every 5 minutes, if the rover
    has moved more than 20 meters from its last reported position, sends an object report.
    """
    aprs = Aprs(host="localhost", port=8001)
    gps = GPS()
    sent = False
    last_report_time = time.time()
    last_report_position = None
    arrived = False

    try:
        await aprs.connect()
    except (AprsError) as e:
        print(f"Initialization error: {e}")
        return

    while not sent:
        try:
            # Use decimal for accurate position checking
            gps_data_dec = gps.get_gps_data_decimal()
            if gps_data_dec is None:
                print("Could not retrieve GPS data. Retrying in 10 seconds...")
                time.sleep(10)
                continue
            lat, lon, tm_iso, _ = gps_data_dec
            distance = haversine(lat, lon, DEST_LAT, DEST_LON)
            print(f"Current position: {lat:.6f}, {lon:.6f} | Distance to destination: {distance:.2f} m")

            # Check for arrival
            if distance <= 20:
                print("Arrived at destination. Sending APRS message...")
                try:
                    # Get DMM and DHM for APRS reporting only when needed
                    gps_data_dmm = gps.get_gps_data_dmm()
                    if gps_data_dmm is None:
                        print("Could not retrieve DMM GPS data for APRS. Retrying in 10 seconds...")
                        time.sleep(10)
                        continue
                    lat_dmm, lon_dmm, tm_dhm, _ = gps_data_dmm

                    aprs.send_my_message_no_ack(
                        mycall=CALLSIGN_FROM,
                        path=APRS_PATH,
                        recipient=CALLSIGN_TO,
                        message="Arrived at destination"
                    )
                    print("APRS message sent.")
                    # Send final object report
                    aprs.send_my_object_no_course_speed(
                        mycall=CALLSIGN_FROM,
                        path=APRS_PATH,
                        time_dhm=tm_dhm,
                        lat_dmm=lat_dmm,
                        long_dmm=lon_dmm,
                        symbol_id="/",
                        symbol_code="O",
                        comment="At destination"
                    )
                    print("Final object report sent: At destination.")
                    sent = True
                    arrived = True
                except AprsError as e:
                    print(f"Failed to send APRS message or object: {e}")
                continue  # Do not check for movement after arrival
            else:
                print("Not within range. Will check again in 10 seconds.")

            # Every 5 minutes, check if rover has moved more than 20m from last report position
            if not arrived:
                now = time.time()
                if last_report_position is None:
                    last_report_position = (lat, lon)
                    last_report_time = now
                elif now - last_report_time >= 300:  # 5 minutes = 300 seconds
                    prev_lat, prev_lon = last_report_position
                    moved = haversine(lat, lon, prev_lat, prev_lon)
                    if moved > 20:
                        print(f"Moved {moved:.2f}m since last report. Sending object report...")
                        try:
                            # Get DMM and DHM for APRS reporting only when needed
                            gps_data_dmm = gps.get_gps_data_dmm()
                            if gps_data_dmm is None:
                                print("Could not retrieve DMM GPS data for APRS. Skipping report.")
                                last_report_time = now
                                continue
                            lat_dmm, lon_dmm, tm_dhm, _ = gps_data_dmm

                            aprs.send_my_object_no_course_speed(
                                mycall=CALLSIGN_FROM,
                                path=APRS_PATH,
                                time_dhm=tm_dhm,
                                lat_dmm=lat_dmm,
                                long_dmm=lon_dmm,
                                symbol_id="/",
                                symbol_code="O",
                                comment="Moving towards destination"
                            )
                            print("Object report sent.")
                            last_report_position = (lat, lon)
                            last_report_time = now
                        except AprsError as e:
                            print(f"Failed to send object report: {e}")
                    else:
                        print(f"Moved only {moved:.2f}m since last report. No report sent.")
                        last_report_time = now  # Reset timer even if not moved enough

            time.sleep(10)
        except GPSError as e:
            print(f"GPS error: {e}")
            time.sleep(10)
        except KeyboardInterrupt:
            print("Exiting.")
            break

if __name__ == "__main__":
    asyncio.run(main())
"""
Example: Calculate a target GPS coordinate using GPS.get_gps_target.

This example demonstrates how to use the aprsrover.gps.GPS.get_gps_target static method
to compute a new latitude and longitude given a starting point, a bearing, and a distance.

Usage:
    python -m examples.gps.sync.dummy.example_gps_target
"""

from aprsrover.gps import GPS

def main() -> None:
    # Example 1: Move 1km east from the equator and prime meridian
    start_lat: float = 0.0
    start_lon: float = 0.0
    bearing: float = 90.0  # East
    distance_cm: int = 100_000  # 1 km

    target_lat, target_lon = GPS.get_gps_target(start_lat, start_lon, bearing, distance_cm)
    print("Example 1:")
    print(f"  Start:   ({start_lat:.6f}, {start_lon:.6f})")
    print(f"  Bearing: {bearing}°")
    print(f"  Distance: {distance_cm/100:.2f} m")
    print(f"  Target:  ({target_lat:.6f}, {target_lon:.6f})\n")

    # Example 2: Move 500m north from (51.5, -0.1)
    start_lat2: float = 51.5
    start_lon2: float = -0.1
    bearing2: float = 0.0  # North
    distance_cm2: int = 50_000  # 500 m

    target_lat2, target_lon2 = GPS.get_gps_target(start_lat2, start_lon2, bearing2, distance_cm2)
    print("Example 2:")
    print(f"  Start:   ({start_lat2:.6f}, {start_lon2:.6f})")
    print(f"  Bearing: {bearing2}°")
    print(f"  Distance: {distance_cm2/100:.2f} m")
    print(f"  Target:  ({target_lat2:.6f}, {target_lon2:.6f})")

if __name__ == "__main__":
    main()
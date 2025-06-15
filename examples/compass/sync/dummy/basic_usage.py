"""
Synchronous compass usage example (dummy backend).

This example reads heading once and prints the result.
Uses: DummyCompass from examples.dummies.compass (no hardware required).
"""
from aprsrover.compass import Compass
from examples.dummies import DummyCompass

def main() -> None:
    compass = Compass(backend=DummyCompass())
    heading = compass.read()
    print(f"Dummy sync Compass: Heading={heading} degrees")

if __name__ == "__main__":
    main()

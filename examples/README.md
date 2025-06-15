# APRSRover Examples

This directory contains usage examples for the `aprsrover` library, organized by module, integration scenario, and backend type. The structure is designed to help you quickly find relevant examples that use dummy (simulated) backends, but can be easily converted for real operations, using synchronous or asynchronous APIs depending on applicability.

## Directory Structure

- `aprs/`, `gps/`, `hw_info/`, `switch/`, `tracks/`, `ultra/`, `servo/`, `neopixel/`: Examples for each individual module.
  - `sync/` and `async/`: Synchronous and asynchronous usage examples.
  - `dummy/`: Dummy backend examples.
- `integration/`: Multi-module integration examples.
- `dummies/`: Central package for all dummy backend classes. Import dummies from here in your examples.

## Example Usage

- To run a dummy backend example for APRS:
  ```python
  from examples.dummies import DummyAPRS
  aprs = DummyAPRS()
  # ...
  ```
- To run a real hardware example, ensure your hardware is connected and configured as required by the example script.

- To run an example from the project root:
  ```sh
  $ PYTHONPATH=src python3 -m examples.aprs.async.dummy.example_aprs_send_my_message_no_ack

  2025-06-08 16:02:40,267 [INFO] root: Connected to KISS TNC at localhost:8001
  2025-06-08 16:02:40,267 [INFO] root: Sent APRS message from N0CALL-1 to DEST-1: Hello, no ACK!
  Message sent (no ACK)
  ```

## Adding New Examples

1. Place new examples in the appropriate module/integration, sync/async, and real/dummy subfolder.
2. Use dummies from the `dummies/` package for all dummy backend examples.
3. Update this README with new example descriptions as needed.

## Modules

- **APRS**: Automatic Packet Reporting System interface
- **GPS**: GPS receiver interface
- **HW Info**: Hardware information (CPU temp, voltage, etc.)
- **Switch**: Hardware switch/button interface
- **Tracks**: Track recording and management
- **UltraSonic**: Ultrasonic distance sensor interface
- **Neopixel**: Neopixel LED control interface
- **DHT**: DHT11/DHT22/AM2302 temperature and humidity sensor interface
- **Compass**: HMC5883L digital compass sensor interface

## Integration Examples

Integration examples demonstrate how to combine multiple modules, e.g., sending an APRS message when arriving at a GPS waypoint.

---

For more details, see the docstrings in each example.

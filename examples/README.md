# APRSRover Examples

This directory contains usage examples for the `aprsrover` library, organized by module, integration scenario, and backend type. The structure is designed to help you quickly find relevant examples for both real hardware and dummy (simulated) backends, and for both synchronous and asynchronous APIs.

## Directory Structure

- `aprs/`, `gps/`, `hw_info/`, `switch/`, `tracks/`: Examples for each individual module.
  - `sync/` and `async/`: Synchronous and asynchronous usage examples.
  - `real/` and `dummy/`: Real hardware and dummy backend examples.
- `integration/`: Multi-module integration examples.
  - `sync/` and `async/` subfolders, each with `real/` and `dummy/` as above.
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
  $ PYTHONPATH=src python3 -m examples.aprs.async.dummy.example_aprs_send_async

  [DummyAPRS] Sending message to N0CALL: Hello from Dummy APRS (async)!
  Message sent: True
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

## Integration Examples

Integration examples demonstrate how to combine multiple modules, e.g., sending an APRS message when arriving at a GPS waypoint.

---

For more details, see the docstrings in each example and the main project README.

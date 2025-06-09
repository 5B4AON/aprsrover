# APRS Module Documentation

## Overview
The APRS module provides utilities for interfacing with a KISS TNC, sending and receiving APRS frames, and supporting both real and dummy backends for testing.

## Features
- Interface with KISS TNC for APRS frame transmission and reception
- Observer pattern for async frame handling
- Send APRS messages, objects, acknowledgements, and position/status reports
- Input validation for all parameters
- Dependency injection for testability
- Custom exception: `AprsError`

## Usage
### Registering Observers and Listening for Messages
```python
from aprsrover.aprs import Aprs
import asyncio

def my_frame_handler(frame):
    print("Received frame:", frame)

async def main():
    aprs = Aprs(host="localhost", port=8001)
    await aprs.connect()
    aprs.register_observer("CALLSIGN", my_frame_handler)
    await aprs.run()
asyncio.run(main())
```

### Sending Messages and Object Reports
```python
aprs.send_my_message_no_ack(
    mycall="CALL-1",
    path=["WIDE1-1"],
    recipient="CALL-2",
    message="Hello APRS"
)
aprs.send_object_report(
    mycall="CALL-1",
    path=["WIDE1-1"],
    time_dhm="011234z",
    lat_dmm="5132.07N",
    long_dmm="00007.40W",
    symbol_id="/",
    symbol_code="O",
    comment="Test object"
)
```

### Dummy KISS Example
```python
from aprsrover.aprs import Aprs, KISSInterface
class DummyKISS(KISSInterface):
    async def create_tcp_connection(self, host, port, kiss_settings):
        class DummyProtocol:
            def write(self, frame): pass
            async def read(self): yield None
        return (None, DummyProtocol())
    def write(self, frame): pass
    def read(self): yield None
aprs = Aprs(kiss=DummyKISS())
aprs.initialized = True
aprs.kiss_protocol = DummyKISS()
```

## Notes
- All hardware access is abstracted for easy mocking in tests.
- See the [examples/README.md](../examples/README.md) for more advanced usage scenarios.

# Switch Module Documentation

## Overview
The Switch module provides a modular, testable interface for managing GPIO-connected switches, supporting both input and output configurations and dummy backends for testing.

## Features
- Manage GPIO-connected switches (input/output)
- Observer pattern for state changes
- Synchronous and asynchronous monitoring
- Input validation for all parameters
- Dependency injection for testability
- Custom exception: `SwitchError`

## Usage
### Input Switch Example
```python
from aprsrover.switch import Switch, SwitchEvent
switch_in = Switch(pin=17, direction="IN")
def on_switch_change(event: SwitchEvent):
    print(f"Switch {event.pin} changed to {'ON' if event.state else 'OFF'}")
switch_in.add_observer(on_switch_change)
switch_in.start_monitoring()
```

### Output Switch Example
```python
switch_out = Switch(pin=18, direction="OUT")
switch_out.set_state(True)
print("Switch state is ON:", switch_out.get_state())
switch_out.set_state(False)
```

### Dummy GPIO Example
```python
from aprsrover.switch import Switch, GPIOInterface
class DummyGPIO(GPIOInterface):
    def __init__(self): self.states = {}
    def setup(self, pin, direction): self.states[pin] = False
    def input(self, pin): return self.states.get(pin, False)
    def output(self, pin, value): self.states[pin] = value
switch = Switch(pin=17, direction="IN", gpio=DummyGPIO())
print("Dummy switch state:", switch.get_state())
```

## Notes
- All hardware access is abstracted for easy mocking in tests.
- See the [examples/README.md](../examples/README.md) for more advanced usage scenarios.

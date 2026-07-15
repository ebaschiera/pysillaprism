# pysillaprism

Transport-agnostic Python client library for the [Silla Prism](https://silla.industries)
EV wallbox, speaking its native **MQTT** protocol (topic manual rel. 4.0).

The library does **not** own an MQTT connection. It parses the Prism topics into
typed state and builds the `command` topics; you wire it to whatever MQTT client
you already have — for example Home Assistant's `mqtt` integration. This keeps
it free of transport dependencies and trivially unit-testable.

## Install

```bash
pip install pysillaprism
```

## Usage

```python
from pysillaprism import PrismDevice, PortMode

# `publish` may be sync or async (e.g. hass mqtt.async_publish).
async def publish(topic: str, payload: str) -> None:
    ...

device = PrismDevice("prism", publish=publish)

# Wire callbacks (all optional).
device.on_status_update = lambda upd: print("changed", upd.field)
device.on_event = lambda ev: print("touch/knock", ev.values)
device.on_command_result = lambda res: print(res.command, res.result)
device.on_hello = lambda info: print("serial", info.serial)

# Subscribe your MQTT client to `device.subscription_topic` ("prism/#")
# and feed every message in:
device.handle_message("prism/1/state", "3")

print(device.status.port(1).state)        # PortState.CHARGING
print(device.status.energy.power_grid)    # signed watts

# Send commands:
await device.set_mode(PortMode.NORMAL)
await device.set_current_limit(9.6)        # amps, for load balancing
await device.set_current_user(16)          # amps, mirrors the +/- buttons
await device.authorize()
```

### Notes on the protocol

- Prism publishes a topic only when its value **changes**, so status fields stay
  `None` until first reported. Status topics are retained on the broker, so a
  fresh subscriber receives the current snapshot immediately.
- The `hello` announcement (which carries the serial and firmware version) is
  sent only when Prism (re)connects and is **not** retained. Treat device info
  as opportunistic: it populates on the next Prism reboot, and the device works
  without it. Identify a device by its base topic, not its serial.
- `power_solar` / `power_house` are only meaningful with a Powerwall/meter
  configured; otherwise Prism publishes `0`.

## License

MIT © Ermanno Baschiera. Not affiliated with Silla S.r.l.

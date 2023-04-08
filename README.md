# pyairtouch

A fully typed asyncio API for the Polyaire AirTouch AC controllers.

The API supports the AirTouch 5.
AirTouch 4 support is planned, but not yet implemented.

A unified public API is provided that encapsulates the underlying AirTouch version.

## Example

```python
import asyncio

import pyairtouch


async def main() -> None:
    # Automatically discover AirTouch devices on the network.
    discovered_airtouches = await pyairtouch.discover()
    if not discovered_airtouches:
        print("No AirTouch discovered")
        return

    for airtouch in discovered_airtouches:
        print(f"Discovered: {airtouch.name} ({airtouch.host})")

    # Work with the first discovered AirTouch (typically there is only one per network)
    airtouch = discovered_airtouches[0]

    # Connect to the AirTouch and read initial state.
    success = await airtouch.init()

    async def _on_ac_status_updated(ac_id: int) -> None:
        aircon = airtouch.air_conditioners[ac_id]
        print(
            f"AC Status  : {aircon.power_state.name} {aircon.mode.name}  "
            f"temp={aircon.current_temp:.1f} set_point={aircon.set_point:.1f}"
        )

        for zone in aircon.zones:
            print(
                f"Zone Status: {zone.name:10} {zone.power_state.name:3}  "
                f"temp={zone.current_temp:.1f} set_point={zone.set_point:.1f} "
                f"damper={zone.current_damper_percentage}"
            )

    # Subscribe to AC status updates:
    for aircon in airtouch.air_conditioners:
        aircon.subscribe(_on_ac_status_updated)

        # Print initial status
        await _on_ac_status_updated(aircon.ac_id)

    # Keep the demo running for a few minutes
    await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(main())
```

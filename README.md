# pyairtouch

![PyPI - Version](https://img.shields.io/pypi/v/pyairtouch)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyairtouch)
![PyPI - License](https://img.shields.io/pypi/l/pyairtouch)
![Tests Status](https://img.shields.io/github/actions/workflow/status/TheNoctambulist/pyairtouch/test.yml?label=tests)


A fully typed asyncio API for the Polyaire AirTouch AC controllers.

The API supports the AirTouch 4 and AirTouch 5.

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

    # In this example we use the first discovered AirTouch (typically there is only one per network)
    airtouch = discovered_airtouches[0]

    # Connect to the AirTouch and read initial state.
    success = await airtouch.init()

    async def _on_ac_status_updated(ac_id: int) -> None:
        aircon = airtouch.air_conditioners[ac_id]
        print(
            f"AC Status  : {aircon.power_state.name} {aircon.mode.name}  "
            f"temp={aircon.current_temperature:.1f} set_point={aircon.target_temperature:.1f}"
        )

        for zone in aircon.zones:
            print(
                f"Zone Status: {zone.name:10} {zone.power_state.name:3}  "
                f"temp={zone.current_temperature:.1f} set_point={zone.target_temperature:.1f} "
                f"damper={zone.current_damper_percentage}"
            )

    # Subscribe to AC status updates:
    for aircon in airtouch.air_conditioners:
        aircon.subscribe(_on_ac_status_updated)

        # Print initial status
        await _on_ac_status_updated(aircon.ac_id)

    # Keep the demo running for a few minutes
    await asyncio.sleep(300)

    # Shutdown the connection
    await airtouch.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

## Say Thank You
If you would like to make a donation as appreciation of my work, please use one of the links below:

<a href="https://coindrop.to/thenoctambulist" target="_blank"><img src="https://coindrop.to/embed-button.png" style="border-radius: 10px; height: 57px !important;width: 229px !important;" alt="Coindrop.to me"/></a>
<a href="https://www.buymeacoffee.com/thenoctambulist" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-blue.png" style="border-radius: 10px; margin-left: 25px" alt="Buy Me A Coffee" height="57px" width="242px"/></a>


import asyncio

import pyairtouch
import sys

# To run this, use the following instructions
# pdm build
# pdm install
# pdm run python3 examples/scan.py

async def monitor_airtouch(airtouch: pyairtouch.AirTouch, duration: int) -> None:
    # Connect to the AirTouch and read initial state.
    print(f"About to initialise {airtouch.name} ({airtouch.host})")
    success = await airtouch.init()
    print(f"Initialisation complete")

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
    if duration > 0:
        print(f"Monitoring for {duration} seconds")
        await asyncio.sleep(duration)

    # Shutdown the connection
    print(f"About to shutown the connection to {airtouch.name} ({airtouch.host})")
    await airtouch.shutdown()
    print(f"Shutdown complete")

async def main() -> None:
    # Automatically discover AirTouch devices on the network.
    print("About to attempt to discover AirTouch devices")
    should_discover = True
    if should_discover:
        discovered_airtouches = await pyairtouch.discover()
        if not discovered_airtouches:
            print("No AirTouch devices discovered")
        else:
            print(f"Discovered: {len(discovered_airtouches)} AirTouch devices")
            for airtouch in discovered_airtouches:
                print(f"  {airtouch.name} ({airtouch.host})")
    else:
        print("Skipping AirTouch discovery")
        discovered_airtouches = []

    args = sys.argv[1:]
    hostOrName = None
    if len(args) == 1:
        # If a single argument is provided, assume it is the host of the AirTouch
        hostOrName = args[0]
    airtouch = None
    if hostOrName is not None:
        for local_airtouch in discovered_airtouches:
            if local_airtouch.host == hostOrName or local_airtouch.name == hostOrName:
                airtouch = local_airtouch
                print(f"Using specified AirTouch (that was discovered): {airtouch.name} ({airtouch.host})")
                break
        if airtouch is None:
            specified_airtouches = await pyairtouch.discover(hostOrName)
            if len(specified_airtouches) > 0:
                airtouch = specified_airtouches[0]
                if len(specified_airtouches) == 1:
                    print(f"Using specified AirTouch (that was not automatically discovered): {airtouch.name} ({airtouch.host})")
                else:
                    print(f"Using first specified AirTouch (out of {len(specified_airtouches)} possibilities): {airtouch.name} ({airtouch.host})")
            else:
                print(f"Unable to find specified AirTouch {hostOrName}")



    if airtouch is None:
        if len(discovered_airtouches) == 1:
            airtouch = discovered_airtouches[0]
            print(f"Using the only discovered AirTouch: {airtouch.name} ({airtouch.host})")
        elif len(discovered_airtouches) > 1:
            airtouch = discovered_airtouches[0]
            print(f"Using the first discovered AirTouch (of {len(discovered_airtouches)}): {airtouch.name} ({airtouch.host})")
    
    if airtouch is not None:
        await monitor_airtouch(airtouch, 300)
    else:
        print(f"Unable to connect to AirTouch")


if __name__ == "__main__":
    asyncio.run(main())
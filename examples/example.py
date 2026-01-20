"""An example demonstrating usage of the pyairtouch API.

Demonstrates discovery of AirTouch systems and monitoring of their status.

To run the example use the command `pdm run example`."""

import argparse
import asyncio
import contextlib
import logging
import sys

import pyairtouch


def msg(msg: str) -> None:
    print(msg, file=sys.stderr)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Briefly monitors discovered AirTouch devices."
    )
    p.add_argument(
        "--host",
        dest="airtouch_host",
        help="Connect to a specified AirTouch console by host name. "
        "If not specified, automatic discovery will be used.",
        type=str,
    )
    p.add_argument(
        "--duration",
        help="Runtime for the example program in seconds. "
        "Defaults to 300 seconds (5 minutes)",
        type=float,
        default=300.0,
        required=False,
    )
    p.add_argument(
        "--debug",
        help="Enable debug logging.",
        action="store_true",
        default=False,
        required=False,
    )
    return p.parse_args()


def _airtouch_id(airtouch: pyairtouch.AirTouch) -> str:
    return f"{airtouch.name} ({airtouch.host})"


def _format_temp(temperature: float | None) -> str:
    if temperature:
        return f"{temperature:2.1f}"
    return "--.-"


async def _monitor_airtouch(airtouch: pyairtouch.AirTouch, duration: float) -> None:
    """Monitor an AirTouch for a fixed duration."""
    success = await airtouch.init()
    if not success:
        msg(f"{_airtouch_id(airtouch)} initialisation failed")
        return

    msg(f"{_airtouch_id(airtouch)} initialised. Monitoring for {duration} seconds")

    async def _on_ac_status_updated(ac_id: int) -> None:
        msg(f"{_airtouch_id(airtouch)} AC {ac_id} status updated")
        aircon = airtouch.air_conditioners[ac_id]
        msg(
            f"  AC Status  : "
            f"{aircon.power_state.name if aircon.power_state else 'Unknown'} "
            f"{aircon.active_mode.name if aircon.active_mode else 'Unknown'} "
            f"{aircon.active_fan_speed.name if aircon.active_fan_speed else 'Unknown'} "
            f"off-timer={aircon.next_quick_timer(pyairtouch.AcTimerType.OFF_TIMER)} "
            f"on-timer={aircon.next_quick_timer(pyairtouch.AcTimerType.ON_TIMER)} "
            f"temp={_format_temp(aircon.current_temperature)} "
            f"set_point={_format_temp(aircon.target_temperature)}"
        )

        for zone in aircon.zones:
            msg(
                f"  Zone Status: {zone.name:10} "
                f"{zone.power_state.name if zone.power_state else 'Unknown':3}  "
                f"temp={_format_temp(zone.current_temperature)} "
                f"set_point={_format_temp(zone.target_temperature)} "
                f"damper={zone.current_damper_percentage}"
            )
        msg("")  # Blank line to separate from subsequent logs.

    # Subscribe to AC status updates:
    for aircon in airtouch.air_conditioners:
        aircon.subscribe(_on_ac_status_updated)

        # Print initial status
        await _on_ac_status_updated(aircon.ac_id)

    # Run the monitor for the specified duration
    await asyncio.sleep(duration)

    await airtouch.shutdown()


async def main(args: argparse.Namespace) -> None:
    # Automatically discover AirTouch devices on the network.
    if args.airtouch_host:
        print(f"Searching for AirTouch at {args.airtouch_host}")
    else:
        print("Searching for all AirTouch systems on the network")

    discovered_airtouches = await pyairtouch.discover(args.airtouch_host)
    if not discovered_airtouches:
        print("No AirTouch discovered")
        return

    print(f"Discovered {len(discovered_airtouches)} AirTouch systems:")
    for airtouch in discovered_airtouches:
        print(f"  {airtouch.name} ({airtouch.host})")

    # Monitor all discovered AirTouch systems
    async with asyncio.TaskGroup() as tg:
        for airtouch in discovered_airtouches:
            tg.create_task(_monitor_airtouch(airtouch, args.duration))


if __name__ == "__main__":
    args = parse_args()

    # Turn on logging
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(stream=sys.stderr, level=level)

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main(args))

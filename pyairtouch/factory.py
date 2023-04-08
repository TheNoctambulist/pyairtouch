"""Factory functions for constructing instances of the AirTouch API."""

import asyncio
import logging
from typing import Optional

import pyairtouch.api
import pyairtouch.at4.comms.discovery as at4_discovery
import pyairtouch.at5.api as at5_api
import pyairtouch.at5.comms.discovery as at5_discovery
import pyairtouch.at5.comms.registry as at5_registry
import pyairtouch.comms.discovery
import pyairtouch.comms.socket
from pyairtouch import comms

_LOGGER = logging.getLogger(__name__)


def connect(  # noqa: PLR0913
    version: pyairtouch.api.AirTouchVersion,
    host: str,
    port: int,
    *,
    airtouch_id: Optional[str] = None,
    name: Optional[str] = None,
    serial: Optional[str] = None,
) -> pyairtouch.api.AirTouch:
    """Connect to a previously discovered AirTouch system.

    This factory function can be used to connect to a known AirTouch system
    whether that was previously discovered, or from manually entered
    configuration.

    If the optional parameters are not provided, internally generated values
    will be used.

    Args:
        version: The version of the AirTouch system being connected to.
        host: Host name of the AirTouch console.
        port: Remote port number of the AirTouch console.
        airtouch_id: Optional AirTouch system ID if known.
        name: Optional human readable AirTouch system name if known.
        serial: Optional serial number for the AirTouch console if known.
    """
    if not airtouch_id:
        airtouch_id = "<airtouch-1>"

    if not name:
        name = version.value

    if not serial:
        # If no serial is provided, generate something likely to be reasonably unique.
        serial = f"{host}-{port}"

    match version:
        case pyairtouch.api.AirTouchVersion.VERSION_4:
            factory = _connect_airtouch_4
        case pyairtouch.api.AirTouchVersion.VERSION_5:
            factory = _connect_airtouch_5
    return factory(host, port, airtouch_id, name, serial)


def _connect_airtouch_4(
    host: str,  # noqa: ARG001
    port: int,  # noqa: ARG001
    airtouch_id: str,  # noqa: ARG001
    name: str,  # noqa: ARG001
    serial: str,  # noqa: ARG001
) -> pyairtouch.api.AirTouch:
    raise NotImplementedError("AirTouch 4 protocol not implemented yet.")


def _connect_airtouch_5(
    host: str,
    port: int,
    airtouch_id: str,
    name: str,
    serial: str,
) -> at5_api.AirTouch5:
    """Connect to an AirTouch 5 console."""
    socket = pyairtouch.comms.socket.AirTouchSocket(
        host=host,
        port=port,
        registry=at5_registry.INSTANCE,
    )

    return at5_api.AirTouch5(
        airtouch_id=airtouch_id,
        serial=serial,
        name=name,
        socket=socket,
    )


async def discover() -> list[pyairtouch.api.AirTouch]:
    """Automatically discover and connect to any AirTouch devices on the network.

    Returns:
        A list of discovered AirTouch instances.
        If no AirTouch devices are discovered on the network, the returned list
        will be empty.
    """
    airtouches: list[pyairtouch.api.AirTouch] = []

    responses = await _search()

    for response in responses:
        match response:
            case at4_discovery.At4DiscoveryResponse():
                _LOGGER.warning(
                    "Discovered AirTouch 4 device. "
                    "AirTouch 4 support not implemented yet."
                )
            case at5_discovery.At5DiscoveryResponse():
                airtouch_5 = _connect_airtouch_5(
                    host=response.host,
                    port=pyairtouch.at5.api.DEFAULT_PORT_NUMBER,
                    airtouch_id=response.airtouch_id,
                    name=response.name,
                    serial=response.serial,
                )
                airtouches.append(airtouch_5)

    return airtouches


_AnyDiscoveryRequest = (
    at4_discovery.At4DiscoveryRequest | at5_discovery.At5DiscoveryRequest
)
_AnyDiscoveryResponse = (
    at4_discovery.At4DiscoveryResponse | at5_discovery.At5DiscoveryResponse
)


async def _search() -> list[comms.DiscoveryResponse]:
    """Discover any AirTouch devices on the network.

    Returns a list containing details of any discovered AirTouch device.
    """
    discoverers: list[
        pyairtouch.comms.discovery.AirTouchDiscoverer[
            _AnyDiscoveryRequest, _AnyDiscoveryResponse
        ]
    ] = [
        pyairtouch.comms.discovery.AirTouchDiscoverer(at4_discovery.CONFIG),
        pyairtouch.comms.discovery.AirTouchDiscoverer(at5_discovery.CONFIG),
    ]

    responses: list[comms.DiscoveryResponse] = []
    for search in asyncio.as_completed([d.search() for d in discoverers]):
        responses.extend(await search)

    return responses

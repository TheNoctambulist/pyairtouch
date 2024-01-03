"""Defines the API data model for pyairtouch.

The data model is designed to be common across the different supported AirTouch
versions.
"""

from collections.abc import Awaitable, Callable, Sequence
from enum import Enum, auto
from typing import Any, Optional, Protocol

# fmt: off
__all__ = [
    # API Enumerations
    "AirTouchVersion",
    "AcPowerState", "AcPowerControl", "AcMode", "AcFanSpeed", "AcSpillState",
    "ZonePowerState", "ZoneControlMethod", "SensorBatteryStatus",

    # API Interfaces
    "UpdateSubscriber",
    "Zone", "AirConditioner", "AirTouch"
]
# fmt: on


class AirTouchVersion(Enum):
    """Supported AirTouch versions.

    The value for each enum can be used as a display string.
    """

    VERSION_4 = "AirTouch 4"
    VERSION_5 = "AirTouch 5"


class AcPowerState(Enum):
    """The power state of an Air-Conditioner."""

    OFF = auto()
    ON = auto()
    OFF_AWAY = auto()
    ON_AWAY = auto()
    SLEEP = auto()


class AcPowerControl(Enum):
    """Options for controlling the power state of an Air-Conditiner."""

    TOGGLE = auto()
    TURN_OFF = auto()
    TURN_ON = auto()
    SET_TO_AWAY = auto()
    SET_TO_SLEEP = auto()


class AcMode(Enum):
    """The operating modes of an Air-Conditioner."""

    AUTO = auto()
    HEAT = auto()
    DRY = auto()
    FAN = auto()
    COOL = auto()

    AUTO_HEAT = auto()
    """Indicates that the AC is in AUTO mode and heating."""

    AUTO_COOL = auto()
    """Indicates that the AC is in AUTO mode and cooling."""


class AcFanSpeed(Enum):
    """The fan speeds of an Air-Conditioner."""

    AUTO = auto()
    QUIET = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    POWERFUL = auto()
    TURBO = auto()
    INTELLIGENT_AUTO = auto()


class AcSpillState(Enum):
    """The spill state of an Air-Conditioner.

    Identifies whether the Air-Conditioner's spill or bypass mode is active.
    Bypass mode is only supported in ACs that have a bypass duct installed.
    """

    NONE = auto()
    SPILL = auto()
    BYPASS = auto()


class ZonePowerState(Enum):
    """Identifies the current power state of an AirTouch zone."""

    OFF = auto()
    ON = auto()
    TURBO = auto()


class ZoneControlMethod(Enum):
    """Control methods for an AirTouch Zone.

    Identifies whether the AirTouch zone is controlled by a temperature
    set-point or set to a fixed damper opening.
    """

    DAMPER = auto()
    TEMP = auto()


class SensorBatteryStatus(Enum):
    """Identifies whether or not the Zone Sensor's batter is running low."""

    NORMAL = auto()
    LOW = auto()


UpdateSubscriber = Callable[[int], Awaitable[Any]]
"""An interface for subscribing to Air Conditioner or Zone updates.

The subscriber will be passed the zone or AC ID that has been updated.
"""


class Zone(Protocol):
    """Interface for a single zone in an AirTouch system."""

    @property
    def zone_id(self) -> int:
        """The ID of the zone.

        Zone IDs are unique across an AirTouch instance.
        """

    @property
    def name(self) -> str:
        """The display name of the zone as configured in the AirTouch system."""

    @property
    def supported_power_states(self) -> Sequence[ZonePowerState]:
        """Set of Zone Power States supported by the zone."""

    @property
    def power_state(self) -> ZonePowerState:
        """The current power state of the zone."""

    @property
    def control_method(self) -> ZoneControlMethod:
        """The current control method of the zone."""

    @property
    def has_temp_sensor(self) -> bool:
        """Whether this zone has a temperature sensor."""

    @property
    def sensor_battery_status(self) -> SensorBatteryStatus:
        """Current batter status of the temperature sensor.

        If the zone doesn't have a temperature sensor, NORMAL is returned.
        """

    @property
    def current_temp(self) -> Optional[float]:
        """The current measured temperature of the zone.

        Returns:
            The current measured temperature of this zone or None if the zone
            doesn't have a temperature sensor.
        """

    @property
    def set_point(self) -> Optional[float]:
        """The current set-point temperature of the zone.

        Returns:
            The current set-point temperature of the zone or None if the zone
            doesn't have a sensor and no set-point is defined.
        """

    @property
    def set_point_resolution(self) -> float:
        """The resolution of the set-point for the zone.

        Values returned from the set_point property will have this resolution.
        When setting a new set-point, the requested value will be rounded to
        this resolution.
        """

    @property
    def current_damper_percentage(self) -> int:
        """Current damper opening percentage.

        Returns:
            The current damper opening percentage as a integer in the range [0, 100].
        """

    @property
    def spill_active(self) -> bool:
        """Whether this zone is currently acting as a spill zone."""

    async def set_power(self, power_control: ZonePowerState) -> None:
        """Set a new power state for the zone.

        Raises:
            ValueError: If the zone does not support the requested power state.
        """

    async def set_set_point(self, set_point: float) -> None:
        """Set a new temperature set-point for the zone.

        Args:
            set_point: The new set-point. The provided value will be rounded
                according to set_point_resolution.

        Raises:
            ValueError: If the zone does not have a temperature sensor.
        """

    async def set_damper_percentage(self, open_percentage: int) -> None:
        """Set the zone to a specific damper percentage.

        Note: For zones that have a temperature sensor it's not recommended to
        use damper percentages since this will interfere with the optimal
        performance of the AirTouch.

        Args:
            open_percentage: The requested damper opening in the range [0, 100].
        """

    def subscribe(self, subscriber: UpdateSubscriber) -> None:
        """Subscribe to be notified of updates to the zone.

        Has no effect if the subscriber is already subscribed.
        """

    def unsubscribe(self, subscriber: UpdateSubscriber) -> None:
        """Unsubscribe from receiving notifications of updates to the zone.

        Has no effect if the subscriber is not subscribed.
        """


class AirConditioner(Protocol):
    """The interface for a single Air-Conditioner in an AirTouch system."""

    @property
    def ac_id(self) -> int:
        """The ID of the air-conditioner."""

    @property
    def supported_power_controls(self) -> Sequence[AcPowerControl]:
        """Set of AC Power Controls supported by the air-conditioner."""

    @property
    def supported_modes(self) -> Sequence[AcMode]:
        """Set of AC Modes supported by the air-conditioner."""

    @property
    def supported_fan_speeds(self) -> Sequence[AcFanSpeed]:
        """Set of Fan Speeds supported by the air-conditioner."""

    @property
    def power_state(self) -> AcPowerState:
        """Current power state of the air-conditioner."""

    @property
    def mode(self) -> AcMode:
        """Current mode of the air-conditioner."""

    @property
    def fan_speed(self) -> AcFanSpeed:
        """Current fan speed of the air-conditioner."""

    @property
    def current_temp(self) -> float:
        """Current temperature as measured by the air-conditioner's sensor.

        Returns:
            The current temperature in degrees celsius.
        """

    @property
    def set_point(self) -> float:
        """Current temperature set-point of the air-conditioner.

        Returns:
            The current set-point temperature in degrees celsius.
        """

    @property
    def set_point_resolution(self) -> float:
        """The resolution of the set-point for the air-conditioner.

        Values returned from the set_point property will have this resolution.
        When setting a new set-point, the requested value will be rounded to
        this resolution.
        """

    @property
    def min_set_point(self) -> float:
        """Minimum permitted value for the set-point of the air-conditioner.

        The minimum set-point may change depending on the mode of the air-conditioner.

        Returns:
            The minimum set-point temperature in degrees celsius.
        """

    @property
    def max_set_point(self) -> float:
        """Maximum permitted value for the set-point of the air-conditioner.

        The maximum set-point may change depending on the mode of the air-conditioner.

        Returns:
            The maximum set-point temperature in degrees celsius.
        """

    @property
    def spill_state(self) -> AcSpillState:
        """Whether the air-conditioner spill or bypass feature is active."""

    @property
    def zones(self) -> Sequence[Zone]:
        """The set of AirTouch zones associated with this Air-Conditioner."""

    async def set_power(self, power_control: AcPowerControl) -> None:
        """Set a new power state for the air-conditioner.

        Raises:
            ValueError: If the requested power control is not supported.
        """

    async def set_mode(self, mode: AcMode, *, power_on: bool = False) -> None:
        """Set a new mode for the air-conditioner.

        Sets a new mode for the air-conditioner and optionally powers on the
        air-conditioner if it is currently turned off.

        Args:
            mode: The new air-conditioner mode
            power_on: If true, update the air-conditioner power state if it is
                currently turned off.

        Raises:
            ValueError: The requested mode is not supported.
        """

    async def set_fan_speed(self, fan_speed: AcFanSpeed) -> None:
        """Set a new fan speed for the air-conditioner.

        Args:
            fan_speed: The new air-conditioner fan speed.

        Raises:
            ValueError: The requested fan speed is not supported.
        """

    async def set_set_point(self, set_point: float) -> None:
        """Set a new temperature set-point for the air-conditioner.

        Changing the set-point will have no effect when zones are using
        temperature sensors.
        TODO: Derive the specific conditions for when this is valid and
        provide a query to check for that state.

        Args:
            set_point: The new set-point value. The requested set-point will be
                rounded to the `set_point_resolution` and bounded by `min_set_point`
                and `max_set_point`.
        """

    def subscribe(self, subscriber: UpdateSubscriber) -> None:
        """Subscribe to notifications of updates to the air-conditioner.

        The subscriber will be notified if the state of the air-conditioner or
        any included zones changes.

        Has no effect if the subscriber is already subscribed.
        """

    def unsubscribe(self, subscriber: UpdateSubscriber) -> None:
        """Unsubscribe from update notifications.

        Has no effect if the subscriber is not subscribed.
        """

    def subscribe_ac_state(self, subscriber: UpdateSubscriber) -> None:
        """Subscribe to air-conditioner state updates.

        Subscribers will be notified of updates to the air-conditioner state only.
        Updates to included zones will not trigger a notification.

        Has no effect if the subscriber is already subscribed.
        """

    def unsubscribe_ac_state(self, subscriber: UpdateSubscriber) -> None:
        """Unsubcribe from air-conditioner state updates.

        Has no effect if the subscriber is not subscribed.
        """


class AirTouch(Protocol):
    """The main interface to an AirTouch system."""

    async def init(self) -> bool:
        """Initialises the AirTouch API and connects to the AirTouch system.

        Returns:
            True if the AirTouch has been succesfully initalised, false otherwise.
        """

    @property
    def initialised(self) -> bool:
        """Whether the AirTouch system has been initialised."""

    @property
    def airtouch_id(self) -> str:
        """The ID of this AirTouch system."""

    @property
    def serial(self) -> str:
        """The serial number of this AirTouch system."""

    @property
    def name(self) -> str:
        """The name of this AirTouch system."""

    @property
    def host(self) -> str:
        """The host name or IP address of this AirTouch system."""

    @property
    def version(self) -> AirTouchVersion:
        """The version of this AirTouch system."""

    @property
    def air_conditioners(self) -> Sequence[AirConditioner]:
        """The set of Air Conditioners integrated with this AirTouch system."""

from dataclasses import dataclass
from enum import Enum


class DeviceType(Enum):
    CO_ALARM = "0000"
    WATER_ALARM = "0004"
    HEAT_ALARM = "0003"
    FIRE_ALARM = "0005"
    DOOR_WINDOW_SENSOR = "0101"


@dataclass
class Device:
    id: str
    name: str
    battery_level: int
    device_state: str
    device_type: DeviceType


class DeviceDict(dict):
    def __init__(self, seq=None, **kwargs):
        if seq is None:
            seq = []
        super().__init__(seq, **kwargs)

    def __missing__(self, key):
        self[key] = Device(key, "", 100, "", None)
        return self[key]

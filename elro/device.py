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
    def __init__(self, factory, seq=None, **kwargs):
        super().__init__(seq, **kwargs)
        self.factory = factory

    def __missing__(self, key):
        self[key] = self.factory(key)

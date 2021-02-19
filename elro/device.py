from enum import Enum
import trio


class DeviceType(Enum):
    CO_ALARM = "0000"
    WATER_ALARM = "0004"
    HEAT_ALARM = "0003"
    FIRE_ALARM = "0005"
    DOOR_WINDOW_SENSOR = "0101"


class Device:
    def __init__(self, id, name, battery_level, device_state, device_type):
        self.id = id
        self.name = name
        self._battery_level = battery_level
        self._device_state = device_state
        self.device_type = device_type
        self.updated = trio.Event()
        self.alarm = trio.Event()

    @property
    def device_state(self):
        return self._device_state

    @device_state.setter
    def device_state(self, device_state):
        self._device_state = device_state
        self._send_update_event()

    @property
    def battery_level(self):
        return self._battery_level

    @battery_level.setter
    def battery_level(self, battery_level):
        self._battery_level = battery_level
        self._send_update_event()

    def _send_update_event(self):
        self.updated.set()
        self.updated = trio.Event()

    def send_alarm_event(self):
        self.alarm.set()
        self.alarm = trio.Event()


class DeviceDict(dict):
    def __init__(self, seq=None, **kwargs):
        if seq is None:
            seq = []
        super().__init__(seq, **kwargs)

    def __missing__(self, key):
        self[key] = Device(key, "", 100, "", None, trio.Event())
        return self[key]

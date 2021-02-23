from enum import Enum
from abc import ABC, abstractmethod
import logging
import json

import trio


class DeviceType(Enum):
    CO_ALARM = "0000"
    WATER_ALARM = "0004"
    HEAT_ALARM = "0003"
    FIRE_ALARM = "0005"
    DOOR_WINDOW_SENSOR = "0101"


class Device(ABC):
    def __init__(self, device_id, device_type):
        self.id = device_id
        self.name = ""
        self._battery_level = -1
        self._device_state = ""
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

    def update(self, data):
        self.device_type = data["data"]["device_name"]

        # set battery status
        batt = int(data["data"]["device_status"][2:4], 16)
        self.battery_level = batt

        self.device_state = "Unknown"
        self.update_specifics(data)
        self._send_update_event()

    @abstractmethod
    def update_specifics(self, data):
        pass

    def __str__(self):
        return f"<{self.device_type}: {self.name} (id: {self.id})>"

    def __repr__(self):
        return str(self)

    @property
    def json(self):
        return json.dumps({"name": self.name,
                           "id": self.id,
                           "type": self.device_type,
                           "state": self.device_state,
                           "battery": self.battery_level})


class WindowSensor(Device):
    def __init__(self, device_id):
        super().__init__(device_id, "0101")

    def update_specifics(self, data):
        if data["data"]["device_name"] != DeviceType.DOOR_WINDOW_SENSOR.value:
            AttributeError(f"Tried to update a window sensor to type "
                           f"{DeviceType(data['data']['device_name'])}")

        if data["data"]["device_status"][4:-2] == "55":
            logging.debug("Door/window id " + str(self.id) + " open!")
            self.device_state = "Open"
        elif data["data"]["device_status"][4:-2] == "AA":
            logging.debug("Door/window id " + str(self.id) + " closed!")
            self.device_state = "Closed"


class AlarmSensor(Device):
    def __init__(self, device_id, device_type):
        super().__init__(device_id, device_type)

    def update_specifics(self, data):
        if data["data"]["device_status"][4:-2] == "BB":
            self.device_state = "Alarm"
        elif data["data"]["device_status"][4:-2] == "AA":
            self.device_state = "Normal"


def create_device_from_data(data):
    if data["data"]["device_name"] == DeviceType.DOOR_WINDOW_SENSOR.value:
        return WindowSensor(data["data"]["device_ID"])
    else:
        return AlarmSensor(data["data"]["device_ID"], data["data"]["device_name"])
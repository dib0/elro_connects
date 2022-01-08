from enum import Enum
from abc import ABC, abstractmethod
import logging
import json

import trio


class DeviceType(Enum):
    """
    The DeviceType defines which kind of Elro device this is
    """
    CO_ALARM = "0000"
    WATER_ALARM = "0004"
    HEAT_ALARM = "0003"
    FIRE_ALARM = "0005"
    DOOR_WINDOW_SENSOR = "0101"


class Device(ABC):
    """
    A Device is an Elro device that is connected to the system
    """
    def __init__(self, device_id, device_type):
        """
        Constructor
        :param device_id: The device ID
        :param device_type: The device type
        """
        self.id = device_id
        self._name = ""
        self._battery_level = -1
        self._device_state = ""
        self.device_type = device_type
        self.updated = trio.Event()
        self.alarm = trio.Event()

    @property
    def name(self):
        """
        The name of the device
        :return: The name
        """
        return self._name

    @name.setter
    def name(self, name):
        self._name = name
        self._send_update_event()

    @property
    def device_state(self):
        """
        The current state of the device as a string
        :return: The device state
        """
        return self._device_state

    @device_state.setter
    def device_state(self, device_state):
        self._device_state = device_state
        self._send_update_event()

    @property
    def battery_level(self):
        """
        The current battery level of the device in percent.
        :return: The battery level
        """
        return self._battery_level

    @battery_level.setter
    def battery_level(self, battery_level):
        self._battery_level = battery_level
        self._send_update_event()

    def _send_update_event(self):
        """
        Triggers the self.updated event
        """
        self.updated.set()
        self.updated = trio.Event()

    def send_alarm_event(self):
        """
        Triggers the self.alarm event.
        """
        self.device_state = 'Alarm'
        self.alarm.set()
        self.alarm = trio.Event()

    def update(self, data, state="Unknown"):
        """
        Updates this device with the data received from the actual device
        :param data: The data dict received from the actual device
        """
        self.device_type = data["data"]["device_name"]

        # set battery status
        batt = int(data["data"]["device_status"][2:4], 16)
        self.battery_level = batt

        self.device_state = state
        self.update_specifics(data)
        self._send_update_event()

    @abstractmethod
    def update_specifics(self, data):
        """
        An abstract method that is called to update type specific things.
        :param data: The data dict received from the actual device
        """
        pass

    def __str__(self):
        return f"<{self.device_type}: {self.name} (id: {self.id})>"

    def __repr__(self):
        return str(self)

    @property
    def json(self):
        """
        A json representation of the device.
        :return: A str containing json.
        """
        return json.dumps({"name": self.name,
                           "device_name": self.name,
                           "id": self.id,
                           "type": self.device_type,
                           "state": self.device_state,
                           "battery": self.battery_level})


class WindowSensor(Device):
    """
    A sensor that can detect open/close state of a window.
    """
    def __init__(self, device_id):
        """
        Constructor
        :param device_id: The device ID
        """
        super().__init__(device_id, "0101")

    def update_specifics(self, data):
        """
        Updates the window "Open"/"Closed" state
        :param data: The data dict received from the actual device
        """
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
    """
    A device that can ring an alarm (HeatAlarm, WaterAlarm, FireAlarm, COAlarm)
    """
    def __init__(self, device_id, device_type):
        """
        Constructor
        :param device_id: The device ID
        :param device_type: The device type
        """
        super().__init__(device_id, device_type)

    def update_specifics(self, data):
        """
        Updates the alarm state of the device.
        :param data: The data dict received from the actual device
        """
        if data["data"]["device_status"][4:-2] == "BB":
            self.device_state = "Alarm"
        elif data["data"]["device_status"][4:-2] == "AA":
            self.device_state = "Normal"


def create_device_from_data(data):
    """
    Factory method to create a device from a data dict
    :param data: The data dict received from the actual device
    :return: A Device object
    """
    if data["data"]["device_name"] == DeviceType.DOOR_WINDOW_SENSOR.value:
        return WindowSensor(data["data"]["device_ID"])
    else:
        return AlarmSensor(data["data"]["device_ID"], data["data"]["device_name"])
from enum import Enum
from abc import ABC, abstractmethod
import logging
import json

import trio


class DeviceType(Enum):
    """
    The DeviceType defines which kind of Elro device this is
    """
    CO_ALARM = "0000","1000","2000","0008","1008","2008","000E","100E","200E"
    WATER_ALARM = "0004","1004","2004","000C","100C","200C","0012","1012","2012"
    HEAT_ALARM = "0003","1003","2003","000B","100B","200B","0011","1011","2011"
    FIRE_ALARM = "0005","1109","2109","000D","100D","200D","0013","1013","2013"
    DOOR_WINDOW_SENSOR = "0101","1101","2101"

    def __new__(cls, *values):
        obj = object.__new__(cls)
        # first value is canonical value
        obj._value_ = values[0]
        for other_value in values[1:]:
            cls._value2member_map_[other_value] = obj
        obj._all_values = values
        return obj

    def __repr__(self):
        return '<%s.%s: %s>' % (
            self.__class__.__name__,
            self._name_,
            ', '.join([repr(v) for v in self._all_values]),
        )


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
        self.device_type_name = DeviceType(device_type).name
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

    def send_alarm_event(self, data):
        """
        Triggers the self.alarm event.
        """
        self.update(data)
        self.alarm.set()
        self.alarm = trio.Event()

    def update(self, data):
        """
        Updates this device with the data received from the actual device
        :param data: The data dict received from the actual device
        """
        self.device_type = data["data"]["device_name"]

        # set battery status
        batt = int(data["data"]["device_status"][2:4], 16)
        self.battery_level = batt

        self.device_state = "Unknown"
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
                           "type_name": self.device_type_name,
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
        if DeviceType(data["data"]["device_name"]) != DeviceType.DOOR_WINDOW_SENSOR:
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
        state = data["data"]["device_status"][4:-2]
        device_type = DeviceType(self.device_type)
        state_name = None

        #CO, WATER and HEAT_ALARM specific status
        if device_type == DeviceType.CO_ALARM or device_type == DeviceType.WATER_ALARM or device_type == DeviceType.HEAT_ALARM:
            if state == "11":
                state_name = "Illegal demolition"
            elif state == "50":
                state_name = "Normal"

        #FIRE_ALARM specific status
        if device_type == DeviceType.FIRE_ALARM:
            if state == "12": 
                state_name = "Fault"
            elif state == "15": 
                state_name = "Silence"
            elif state == "17": 
                state_name = "Test Alarm"
            elif state == "19": 
                state_name = "Fire Alarm"
            elif state == "1B": 
                state_name = "Silence"

        #Generic status
        if state_name == None:
            if state == "BB":
                state_name = "Test Alarm"
            elif state == "55":
                state_name = "Alarm"
            elif state == "AA":
                state_name = "Normal"
            elif state == "FF":
                state_name = "Offline"
            else:
                logging.warning(f"Unable to determine the state with value '{state}'")
                state_name = "Unknown"

        self.device_state = state_name
        logging.debug(f"AlarmSensor with id '{self.id}' has got the device_state '{self.device_state}'")


def create_device_from_data(data):
    """
    Factory method to create a device from a data dict
    :param data: The data dict received from the actual device
    :return: A Device object
    """
    if DeviceType(data["data"]["device_name"]) == DeviceType.DOOR_WINDOW_SENSOR:
        return WindowSensor(data["data"]["device_ID"])
    else:
        return AlarmSensor(data["data"]["device_ID"], data["data"]["device_name"])
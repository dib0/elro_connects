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
    GAS_ALARM = "0002","1002","2002","1006","000A","100A","200A"
    SMOKE_ALARM = "0001","1001","2001","0009","1009","2009"
    WATER_ALARM = "0004","1004","2004","000C","100C","200C","0012","1012","2012"
    HEAT_ALARM = "0003","1003","2003","000B","100B","200B","0011","1011","2011"
    FIRE_ALARM = "0005","1109","2109","000D","100D","200D","0013","1013","2013"

    GUARD = "0210","1210","2210" # access control
    TEMPERATURE_SENSOR = "0102","1102","2102" # TH_CHECK
    DOOR_WINDOW_SENSOR = "0101","1101","2101"   # DOOR_CHECK

    LOCK = "1213"
    MODE_BUTTON = "0305"
    BUTTON = "0301","1301","2301"
    LAMP = "020A","120A","220A"
    SOCKET = "0200","1200","2200"
    TWO_SOCKET = "0201","1201","2201"
    VALVE = "0208","1208","2208"
    CURTAIN = "0209","1209","2209"
    TEMP_CONTROL = "0215","1215","2215"
    DIMMING_MODULE = "0214","1214","2214"

    SOS_KEY = "0300","1300","2300"
    PIR_CHECK = "0100","1100","2100"

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
    def __init__(self, device_id, device_type_id):
        """
        Constructor
        :param device_id: The device ID
        :param device_type: The device type
        """
        self.id = device_id
        self._name = ""
        self._battery_level = -1
        self._signal_strength = -1
        self._device_state = ""
        self.device_type = DeviceType(device_type_id)
        self.device_type_id = device_type_id
        self.device_type_name = self.device_type.name
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

    @property
    def signal_strength(self):
        """
        The current signal strength of the device from 0 to 4.
        :return: The signal strength
        """
        return self._signal_strength

    @signal_strength.setter
    def signal_strength(self, signal_strength):
        self._signal_strength = signal_strength
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
        self.device_type_id = data["data"]["device_name"]

        # set signal status
        sig = int(data["data"]["device_status"][0:2], 16)
        logging.info(f"signal {sig}")
        self.signal_strength = sig

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
        return f"<{self.device_type_id}: {self.name} (id: {self.id})>"

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
                           "type": self.device_type_id,
                           "type_name": self.device_type_name,
                           "state": self.device_state,
                           "battery": self.battery_level,
                           "signal": self.signal_strength})


class WindowSensor(Device):
    """
    A sensor that can detect open/close state of a window.
    """
    def __init__(self, device_id, device_type_id):
        """
        Constructor
        :param device_id: The device ID
        :param device_type_id: The device type id
        """
        super().__init__(device_id, device_type_id)

    def update_specifics(self, data):
        """
        Updates the window "Open"/"Closed" state
        :param data: The data dict received from the actual device
        """
        if DeviceType(data["data"]["device_name"]) != DeviceType.DOOR_WINDOW_SENSOR:
            logging.error(f"Tried to update a window sensor to type '{DeviceType(data['data']['device_name'])}'")

        state = data["data"]["device_status"][4:-2]
        if state == "55":
            logging.debug("Door/window id " + str(self.id) + " open!")
            self.device_state = "Open"
        elif state == "AA":
            logging.debug("Door/window id " + str(self.id) + " closed!")
            self.device_state = "Closed"


class AlarmSensor(Device):
    """
    A device that can ring an alarm (HeatAlarm, WaterAlarm, FireAlarm, COAlarm)
    """
    def __init__(self, device_id, device_type_id):
        """
        Constructor
        :param device_id: The device ID
        :param device_type_id: The device type id
        """
        super().__init__(device_id, device_type_id)

    def update_specifics(self, data):
        """
        Updates the alarm state of the device.
        :param data: The data dict received from the actual device
        """
        state = data["data"]["device_status"][4:-2]
        state_name = None

        #CO, WATER and HEAT_ALARM specific status
        if self.device_type == DeviceType.CO_ALARM or self.device_type == DeviceType.WATER_ALARM or self.device_type == DeviceType.HEAT_ALARM:
            if state == "11":
                state_name = "Illegal demolition"
            elif state == "50":
                state_name = "Normal"

        #FIRE_ALARM specific status
        if self.device_type == DeviceType.FIRE_ALARM:
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
        if state_name is None:
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

class Unsupported(Device):
    """
    Device used when no other match is available.
    """
    def __init__(self, device_id, device_type_id):
        """
        Constructor
        :param device_id: The device ID
        :param device_type_id: The device type id
        """
        logging.warning(f"Creating an unsupported device ({device_id}) type '{DeviceType(device_type_id)}'")
        super().__init__(device_id, device_type_id)

    def update_specifics(self, data):
        """
        :param data: The data dict received from the actual device
        """
        logging.warning(f"Updating an unsupported device type '{self.device_type}'")

        state = data["data"]["device_status"][4:-2]
        if state == "FF":
            logging.debug("Unsupported device with id " + str(self.id) + " offline!")
            self.device_state = "Offline"

def create_device_from_data(data):
    """
    Factory method to create a device from a data dict
    :param data: The data dict received from the actual device
    :return: A Device object
    """
    
    device_id = data["data"]["device_ID"]
    device_type_id = data["data"]["device_name"]

    if device_type_id == "DEL":
        logging.warning(f"Got device_name 'DEL' for device_id '{(device_id)}'")
        return None
    else:
        devType = DeviceType(device_type_id)
        match devType:
            case DeviceType.DOOR_WINDOW_SENSOR:
                return WindowSensor(device_id, device_type_id)
            case DeviceType.CO_ALARM | DeviceType.GAS_ALARM | DeviceType.SMOKE_ALARM | DeviceType.WATER_ALARM | DeviceType.HEAT_ALARM | DeviceType.FIRE_ALARM:
                return AlarmSensor(device_id, device_type_id)
            case _:
                return Unsupported(device_id, device_type_id)

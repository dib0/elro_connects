from unittest.mock import MagicMock

import pytest
import trio

from elro.device import create_device_from_data, WindowSensor, AlarmSensor, DeviceType
from elro.command import Command


@pytest.fixture
def update_data():
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": DeviceType.DOOR_WINDOW_SENSOR.value,
                     "device_ID": "vader",
                     "device_status": "  2AAA  "}}
    return data


@pytest.fixture
def device(update_data):
    device = create_device_from_data(update_data)
    return device


@pytest.fixture
def alarm_device():
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": DeviceType.CO_ALARM.value,
                     "device_ID": "vader",
                     "device_status": "  2AAA  "}}
    device = create_device_from_data(data)
    return device


def test_factory_creates_the_right_type_for_window_sensor():
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": DeviceType.DOOR_WINDOW_SENSOR.value,
                     "device_ID": "vader",
                     "device_status": "  2AAA  "}}
    device = create_device_from_data(data)
    assert isinstance(device, WindowSensor)


def test_factory_creates_the_right_type_for_water_sensor():
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": DeviceType.WATER_ALARM.value,
                     "device_ID": "vader",
                     "device_status": "  2AAA  "}}
    device = create_device_from_data(data)
    assert isinstance(device, AlarmSensor)


def test_factory_creates_the_right_type_for_co_sensor():
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": DeviceType.CO_ALARM.value,
                     "device_ID": "vader",
                     "device_status": "  2AAA  "}}
    device = create_device_from_data(data)
    assert isinstance(device, AlarmSensor)


def test_factory_creates_the_right_type_for_heat_sensor():
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": DeviceType.HEAT_ALARM.value,
                     "device_ID": "vader",
                     "device_status": "  2AAA  "}}
    device = create_device_from_data(data)
    assert isinstance(device, AlarmSensor)


def test_factory_creates_the_right_type_for_fire_sensor():
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": DeviceType.FIRE_ALARM.value,
                     "device_ID": "vader",
                     "device_status": "  2AAA  "}}
    device = create_device_from_data(data)
    assert isinstance(device, AlarmSensor)


def test_calling_update_fires_updated_event(device, update_data):
    event_set = MagicMock()
    device.updated.set = event_set
    device.update(update_data)
    event_set.assert_called_once_with()
    assert isinstance(device.updated, trio.Event)
    assert device.updated.is_set() is False


def test_setting_device_state_fires_updated_event(device, update_data):
    event_set = MagicMock()
    device.updated.set = event_set
    device.device_state = "anakin"
    event_set.assert_called_once_with()


def test_setting_battery_level_fires_updated_event(device, update_data):
    event_set = MagicMock()
    device.updated.set = event_set
    device.battery_level = 42
    event_set.assert_called_once_with()


def test_update_window_sensor_to_open_sets_correct_state(device, update_data):
    device.device_state = "leia"
    update_data['data']['device_status'] = '  2A55  '
    device.update_specifics(update_data)
    assert device.device_state == "Open"


def test_update_window_sensor_to_closed_sets_correct_state(device, update_data):
    device.device_state = "leia"
    update_data['data']['device_status'] = '  2AAA  '
    device.update_specifics(update_data)
    assert device.device_state == "Closed"


def test_update_alarm_sensor_to_normal_sets_correct_state(alarm_device, update_data):
    alarm_device.device_state = 'leia'
    update_data['data']['device_status'] = '  2AAA  '
    alarm_device.update_specifics(update_data)
    assert alarm_device.device_state == "Normal"


def test_update_alarm_sensor_to_alarm_sets_correct_state(alarm_device, update_data):
    alarm_device.device_state = 'leia'
    update_data['data']['device_status'] = '  2ABB  '
    alarm_device.update_specifics(update_data)
    assert alarm_device.device_state == "Alarm"

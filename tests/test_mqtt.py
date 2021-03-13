from asynctest import CoroutineMock, MagicMock
import asynctest
import pytest
import elro.mqtt
from elro.device import AlarmSensor, DeviceType


@pytest.fixture
def client():
    client = elro.mqtt.MQTTPublisher("test", "/test")
    return client


@pytest.fixture
def mock_device():
    device = AlarmSensor("42", DeviceType.DOOR_WINDOW_SENSOR.value)
    device.alarm.wait = CoroutineMock()
    device.updated.wait = CoroutineMock()
    device.name = "yoda"
    return device


async def test_handle_device_alarm_sends_alarm_message(client, mock_device):
    with asynctest.mock.patch("elro.mqtt.open_mqttclient") as mock_open_client:
        mock_open_client.return_value.__aenter__.return_value.publish = CoroutineMock()
        await client.handle_device_alarm(mock_device)
    mock_device.alarm.wait.assert_called_once()
    publisher = mock_open_client.return_value.__aenter__.return_value.publish
    publisher.assert_called_with('/test/elro/yoda', b'alarm', 1)


async def test_handle_device_update_sends_update_message(client, mock_device):
    with asynctest.mock.patch("elro.mqtt.open_mqttclient") as mock_open_client:
        mock_open_client.return_value.__aenter__.return_value.publish = CoroutineMock()
        await client.handle_device_update(mock_device)
    mock_device.updated.wait.assert_called_once()
    publisher = mock_open_client.return_value.__aenter__.return_value.publish
    publisher.assert_called_with('/test/elro/yoda',
                                 b'{"name": "yoda", "id": "42", "type": "0101", "state": "", "battery": -1}',
                                 1)

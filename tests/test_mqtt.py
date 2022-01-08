from asynctest import CoroutineMock, MagicMock
import asynctest
import pytest
import elro.mqtt
from elro.device import AlarmSensor, DeviceType


@pytest.fixture
def client():
    client = elro.mqtt.MQTTPublisher("test", True, "/test")
    return client


@pytest.fixture
def mock_device():
    device = AlarmSensor("42", DeviceType.DOOR_WINDOW_SENSOR.value)
    device.name = "yoda"
    device.alarm.wait = CoroutineMock()
    device.updated.wait = CoroutineMock()
    return device


async def test_handle_device_alarm_sends_alarm_message(client, mock_device):
    with asynctest.mock.patch("elro.mqtt.open_mqttclient") as mock_open_client:
        mock_open_client.return_value.__aenter__.return_value.publish = CoroutineMock()
        await client.handle_device_alarm(mock_device)
    mock_device.alarm.wait.assert_called_once()
    publisher = mock_open_client.return_value.__aenter__.return_value.publish
    publisher.assert_called_with('/test/elro/42',
                                 b'{"name": "yoda", "device_name": "yoda", "id": "42", "type": "0101", "state": "Alarm", "battery": 100}',
                                 1)


async def test_handle_device_update_sends_update_message(client, mock_device):
    with asynctest.mock.patch("elro.mqtt.open_mqttclient") as mock_open_client:
        mock_open_client.return_value.__aenter__.return_value.publish = CoroutineMock()
        await client.handle_device_update(mock_device)
    mock_device.updated.wait.assert_called_once()
    publisher = mock_open_client.return_value.__aenter__.return_value.publish
    publisher.assert_called_with('/test/elro/42',
                                 b'{"name": "yoda", "device_name": "yoda", "id": "42", "type": "0101", "state": "", "battery": -1}',
                                 1)

async def test_handle_device_update_sends_update_message(client, mock_device):
    with asynctest.mock.patch("elro.mqtt.open_mqttclient") as mock_open_client:
        mock_open_client.return_value.__aenter__.return_value.publish = CoroutineMock()
        await client.handle_device_discovery(mock_device)
    publisher = mock_open_client.return_value.__aenter__.return_value.publish
    publisher.assert_called_with('homeassistant/sensor/elro_k1/42',
                                 b'{"name": "elro_k1_42", "state_topic": "test/elro/42", "value_template": "{{ value_json.state }}", "json_attributes_topic": "test/elro/42", "unique_id": "elro_k1_device_42"}',
                                 1)

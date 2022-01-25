import pytest
from asynctest.mock import CoroutineMock, MagicMock
from elro.hub import Hub
from elro.command import Command


@pytest.fixture
async def hub():
    hub = Hub("127.0.0.1", 1025, "ST_aaaaaaaaaaaa")
    hub.sock.sendto = CoroutineMock()
    return hub


@pytest.fixture
def update_data():
    return {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": "0101",
                     "device_ID": "vader",
                     "device_status": "  42AA"}}


async def test_construct_message_generates_correct_message(hub):
    message = hub.construct_message("fortytwo")
    assert message == '{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",' \
                      '"ctrlKey":"0","appTid":"0","data":fortytwo}}'


async def test_send_data_calls_sendto(hub):
    await hub.send_data("fortytwo")
    hub.sock.sendto.assert_awaited_with(b"fortytwo", ("127.0.0.1", 1025))


async def test_get_device_names_sends_the_right_command(hub):
    await hub.get_device_names()
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"0","appTid":"0","data":{"cmdId":14,"device_ID":0}}}',
                                        ('127.0.0.1', 1025))


async def test_sync_devices_sends_the_right_command(hub):
    await hub.sync_devices()
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"0","appTid":"0","data":{"cmdId":15,"device_status":""}}}',
                                        ('127.0.0.1', 1025))


async def test_sync_scenes_sends_the_right_command(hub):
    await hub.sync_scenes(42)
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"0","appTid":"0","data":'
                                        b'{"cmdId":31,"sence_group":42,"answer_content":"","scene_content":""}}}',
                                        ('127.0.0.1', 1025))


async def test_recv_data_sets_connected_on_name_response(hub):
    hub.sock.recv = CoroutineMock(return_value="  NAME:ST_aaaaaaaaaaaa ")
    assert hub.connected == False
    await hub.receive_data()
    assert hub.connected == True


async def test_recv_handles_answer_ok_response_correctly(hub):
    hub.sock.recv = CoroutineMock(return_value="  {ST_answer_OK} ")
    hub.handle_command = MagicMock()
    await hub.receive_data()
    hub.handle_command.assert_not_called()


async def test_recv_handles_commands_correctly(hub):
    hub.sock.recv = CoroutineMock(return_value='  {"params":"fortytwo"} ')
    hub.handle_command = CoroutineMock()
    await hub.receive_data()
    hub.handle_command.assert_awaited_with("fortytwo")


async def test_update_on_new_device_adds_device(hub, update_data):
    size = len(hub.devices)
    await hub.handle_command(update_data)
    assert len(hub.devices) == size + 1


async def test_can_update_window_sensor_to_open(hub):
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": "0101",
                     "device_ID": "vader",
                     "device_status": "  2A55  "}}
    await hub.handle_command(data)
    assert hub.devices["vader"].device_state == "Open"
    assert hub.devices["vader"].battery_level == 42


async def test_can_update_window_sensor_to_closed(hub):
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": "0101",
                     "device_ID": "vader",
                     "device_status": "  2AAA  "}}
    await hub.handle_command(data)
    assert hub.devices["vader"].device_state == "Closed"
    assert hub.devices["vader"].battery_level == 42


async def test_can_update_another_sensor_to_alarm(hub):
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": "0004",
                     "device_ID": "vader",
                     "device_status": "  2ABB  "}}
    await hub.handle_command(data)
    assert hub.devices["vader"].device_state == "Alarm"
    assert hub.devices["vader"].battery_level == 42


async def test_can_update_another_sensor_to_normal(hub):
    data = {"data": {"cmdId": Command.DEVICE_STATUS_UPDATE.value,
                     "device_name": "0004",
                     "device_ID": "vader",
                     "device_status": "  2AAA  "}}
    await hub.handle_command(data)
    assert hub.devices["vader"].device_state == "Normal"
    assert hub.devices["vader"].battery_level == 42


async def test_does_not_crash_on_a_name_reply_on_unregistered_devices(hub):
    data = {"data": {"cmdId": Command.DEVICE_NAME_REPLY.value,
                     "answer_content": "00014040404040576f686e7a696d6d657224"}}
    result = await hub.handle_command(data)
    assert result is None

async def test_set_device_name_sends_right_command(hub):
    await hub.set_device_state(3,"17")
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"25","appTid":"0","data":{"cmdId":1,"device_id":3,"device_status":"17000000"}}}',
                                        ('127.0.0.1', 1025))

async def test_set_device_name_sends_right_command(hub):
    await hub.set_device_name(3,"Kitchen")
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"25","appTid":"0","data":{"cmdId":5,"device_id":3,"device_name":"40404040404040404b69746368656e2493AE"}}}',
                                        ('127.0.0.1', 1025))

async def test_sync_device_status_sends_right_command(hub):
    devices = {}
    devices[3] = "0464AA00"
    devices[5] = "0464AA00"
    await hub.sync_device_status(3,"devices")
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"25","appTid":"0","data":{"cmdId":29,"device_status":"000e000000006B3E000000006B3E"}}}',
                                        ('127.0.0.1', 1025))

async def test_remove_device_sends_right_command(hub):
    await hub.remove_device(3, True)
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"25","appTid":"0","data":{"cmdId":4,"device_ID":3}}}',
                                        ('127.0.0.1', 1025))

async def test_permit_join_device_sends_right_command(hub):
    await hub.permit_join_device(3, True)
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"25","appTid":"0","data":{"cmdId":2}}}',
                                        ('127.0.0.1', 1025))

async def test_permit_join_device_disable_sends_right_command(hub):
    await hub.permit_join_device_disable(3, True)
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"25","appTid":"0","data":{"cmdId":7}}}',
                                        ('127.0.0.1', 1025))

async def test_replace_device_sends_right_command(hub):
    await hub.permit_join_device_disable(3, True)
    hub.sock.sendto.assert_awaited_with(b'{"msgId":1,"action":"appSend","params":{"devTid":"ST_aaaaaaaaaaaa",'
                                        b'"ctrlKey":"25","appTid":"0","data":{"cmdId":3}}}',
                                        ('127.0.0.1', 1025))
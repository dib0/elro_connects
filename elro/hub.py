import logging
import json

import trio
from valideer import accepts
import valideer

from elro.command import Command
from elro.device import create_device_from_data
from elro.utils import get_string_from_ascii


class Hub:
    APP_ID = '0'
    CTRL_KEY = '0'

    @accepts(ip=valideer.Pattern("^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$"),
             port="integer",
             device_id=valideer.Pattern("^ST_([0-9A-Fa-f]{12})$"))
    def __init__(self, ip, port, device_id):
        self.ip = ip
        self.port = port
        self.id = device_id

        self.devices = {}
        self.connected = False

        self.msg_id = 0
        self.sock = trio.socket.socket(trio.socket.AF_INET, trio.socket.SOCK_DGRAM)

    async def sender_task(self):
        await self.connect()
        await self.sync_scenes(0)
        await self.get_device_names()

        # Main loop, keep updating every 30 seconds. Keeps 'connection' alive in order
        # to receive alarms/events
        while True:
            await self.sync_devices()
            await trio.sleep(30)  # sleep first to handle the sync scenes and device names

    async def receiver_task(self):
        while True:
            await self.receive_data()

    async def connect(self):
        print("Start connection with hub.")
        while not self.connected:
            await self.send_data('IOT_KEY?' + self.id)
            await trio.sleep(1)

        msg = self.construct_message('{"cmdId":' + str(Command.SYN_DEVICE_STATUS.value) + ',"device_status":""}')
        await self.send_data(msg)

    def construct_message(self, data):
        self.msg_id += 1

        result = '{"msgId":' + str(self.msg_id) + \
                 ',"action":"appSend","params":{"devTid":"' + \
                 self.id + '","ctrlKey":"' + Hub.CTRL_KEY + '","appTid":"' + Hub.APP_ID + '","data":' + data + '}}'
        return result

    async def send_data(self, data):
        logging.info(f"Send data: {data}")
        await self.sock.sendto(bytes(data, "utf-8"),
                               (self.ip, self.port))

    async def receive_data(self):
        data = await self.sock.recv(4096)

        reply = str(data)[2:-1]
        if reply.endswith('\\n'):
            reply = reply[:-2]
        if reply.endswith('\\r'):
            reply = reply[:-2]

        logging.info('Received data: ' + reply)

        if f"NAME:{self.id}" in reply:
            self.connected = True

        if reply.startswith('{') and reply != "{ST_answer_OK}":
            msg = json.loads(reply)
            dat = msg["params"]

            self.handle_command(dat)

            # Send reply
            await self.send_data('APP_answer_OK')

    def handle_command(self, data):
        logging.info(f"Handle command: {data}")
        if data["data"]["cmdId"] == Command.DEVICE_STATUS_UPDATE.value:
            if data["data"]["device_name"] == "STATUES":
                return

            # set device ID
            d_id = data["data"]["device_ID"]
            try:
                dev = self.devices[d_id]
            except KeyError:
                dev = create_device_from_data(data)
                self.devices[d_id] = dev

            dev.update(data)

        elif data["data"]["cmdId"] == Command.DEVICE_ALARM_TRIGGER.value:
            d_id = int(data["data"]["answer_content"][6:10], 16)
            dev = self.devices[d_id]
            dev.send_alarm_event()
            logging.debug("ALARM!! Device_id " + str(d_id) + "(" + dev.name + ")")

        elif data["data"]["cmdId"] == Command.DEVICE_NAME_REPLY.value:
            answer = data["data"]["answer_content"]
            if answer == "NAME_OVER":
                return

            d_id = int(answer[0:4], 16)
            name_val = get_string_from_ascii(answer[4:])

            dev = self.devices[d_id]
            dev.name = name_val

    async def sync_scenes(self, group_nr):
        msg = self.construct_message('{"cmdId":' + str(Command.SYN_SCENE.value) +
                                     ',"sence_group":' + str(group_nr) + ',"answer_content":"","scene_content":""}')
        logging.info(f"sync scenes, group {group_nr}")
        await self.send_data(msg)

    async def sync_devices(self):
        msg = self.construct_message('{"cmdId":' + str(Command.GET_ALL_EQUIPMENT_STATUS.value) + ',"device_status":""}')
        logging.info("sync devices")
        await self.send_data(msg)

    async def get_device_names(self):
        msg = self.construct_message('{"cmdId":' + str(Command.GET_DEVICE_NAME.value) + ',"device_ID":0}')
        await self.send_data(msg)

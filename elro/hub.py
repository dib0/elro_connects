import logging
import json

import trio
from valideer import accepts
import valideer

from elro.command import Command
from elro.device import create_device_from_data
from elro.utils import get_string_from_ascii
from elro.validation import hostname, ip_address


class Hub:
    """
    A representation of the K1 Connector (its "Hub") of the Elro Connects system
    """
    APP_ID = '0'
    CTRL_KEY = '0'

    @accepts(ip=valideer.Pattern(f"^(mqtt://)?({ip_address})|({hostname})$"),
             port="integer",
             device_id=valideer.Pattern("^ST_([0-9A-Fa-f]{12})$"))
    def __init__(self, ip, port, device_id):
        """
        Constructor
        :param ip: The ip of the K1
        :param port: The port of the K1 (usually 1025)
        :param device_id: The device id of the K1 (starts with ST_ followed by its MAC address without colons)
        """
        self.ip = ip
        self.port = port
        self.id = device_id

        self.devices = {}
        self.unregistered_names = {}
        self.connected = False

        self.msg_id = 0
        self.sock = trio.socket.socket(trio.socket.AF_INET, trio.socket.SOCK_DGRAM)

        self.new_device_send_ch, self.new_device_receive_ch = trio.open_memory_channel(0)

    async def sender_task(self):
        """
        The main loop for sending keep alive messages asking for the current status to
        the K1
        """
        await self.connect()
        await self.sync_scenes(0)
        await self.get_device_names()

        # Main loop, keep updating every 30 seconds. Keeps 'connection' alive in order
        # to receive alarms/events
        while True:
            await trio.sleep(30)  # sleep first to handle the sync scenes and device names
            await self.sync_devices()
            await self.get_device_names()

    async def receiver_task(self):
        """
        The main loop for receiving data from the K1
        """
        while True:
            await self.receive_data()

    async def connect(self):
        """
        Connects with the K1
        """
        print("Start connection with hub.")
        while not self.connected:
            await self.send_data('IOT_KEY?' + self.id)
            await trio.sleep(1)

        msg = self.construct_message('{"cmdId":' + str(Command.SYN_DEVICE_STATUS.value) + ',"device_status":""}')
        await self.send_data(msg)

    def construct_message(self, data):
        """
        Construct a valid message from data
        :param data: A string containing data to be send to the K1
        :return: A json message
        """
        self.msg_id += 1

        result = '{"msgId":' + str(self.msg_id) + \
                 ',"action":"appSend","params":{"devTid":"' + \
                 self.id + '","ctrlKey":"' + Hub.CTRL_KEY + '","appTid":"' + Hub.APP_ID + '","data":' + data + '}}'
        return result

    async def send_data(self, data):
        """
        Sends data to the K1
        :param data: The data to be send
        """
        logging.info(f"Send data: {data}")
        await self.sock.sendto(bytes(data, "utf-8"),
                               (self.ip, self.port))

    async def receive_data(self):
        """
        Receives data from the K1
        """
        i = 0
        while i < 3:
            try:
                data = await self.sock.recv(4096)
                break
            except Exception as Error:
                i = i+1
                if i < 3:
                    logging.warning(f"Unable to connect to k1, retrying again. Error: {Error}")
                    await trio.sleep(1)
                else:
                    logging.error(f"Unable to connect to k1 with error: {Error}")
                    exit()

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

            await self.handle_command(dat)

            # Send reply
            await self.send_data('APP_answer_OK')

    async def create_device(self, data):
        """
        Creates a new device in the device dict
        :param data: The data to create the device from
        :return: The device object
        """
        logging.info(f"Create device with data: {data}")
        dev = create_device_from_data(data)
        d_id = data["data"]["device_ID"]
        if self.unregistered_names.get(d_id):
            dev.name = self.unregistered_names[d_id]
            del self.unregistered_names[d_id]
        self.devices[d_id] = dev
        await self.new_device_send_ch.send(d_id)
        return self.devices[d_id]

    async def handle_command(self, data):
        """
        Handles all commands from the K1
        :param data: The data with the commands
        """
        logging.info(f"Handle command: {data}")
        if data["data"]["cmdId"] == Command.DEVICE_STATUS_UPDATE.value:
            logging.debug(f"Processing cmdId: {data['data']['cmdId']}")
            if data["data"]["device_name"] == "STATUES":
                return

            # set device ID
            d_id = data["data"]["device_ID"]
            try:
                dev = self.devices[d_id]
            except KeyError:
                dev = await self.create_device(data)

            await trio.sleep(0)

            dev.update(data)

        elif data["data"]["cmdId"] == Command.DEVICE_ALARM_TRIGGER.value:
            logging.debug(f"Processing cmdId: {data['data']['cmdId']}")
            d_id = int(data["data"]["answer_content"][6:10], 16)
            try:
                dev = self.devices[d_id]
            except KeyError:
                if data["data"]["cmdId"] == Command.DEVICE_ALARM_TRIGGER.value:
                    logging.warning(f"Got device id '{d_id}', but the device is not yet known. Trying to create the device")
                    d_name = data["data"]["answer_content"][10:14]
                    d_status = data["data"]["answer_content"][14:22]
                    data = {
                        "data": {
                            "cmdId": f"{Command.DEVICE_STATUS_UPDATE.value}",
                            "device_ID": d_id,
                            "device_name": f"{d_name}",
                            "device_status": f"{d_status}"
                        }
                    }
                    dev = await self.create_device(data)
                    await trio.sleep(0)
                    dev.update(data, "Alarm")
                else:
                    logging.error(f"Unable to trigger device alarm, device is not yet known and cannot be created: {data}")
                    return
            dev.send_alarm_event()
            logging.debug("ALARM!! Device_id " + str(d_id) + "(" + dev.name + ")")

        elif data["data"]["cmdId"] == Command.DEVICE_NAME_REPLY.value:
            logging.debug(f"Processing cmdId: {data['data']['cmdId']}")
            answer = data["data"]["answer_content"]
            if answer == "NAME_OVER":
                return

            d_id = int(answer[0:4], 16)
            name_val = get_string_from_ascii(answer[4:])

            try:
                dev = self.devices[d_id]
            except KeyError:
                self.unregistered_names[d_id] = name_val
                return
            await trio.sleep(0)
            dev.name = name_val

    async def sync_scenes(self, group_nr):
        """
        Sends a sync scene command to the K1
        :param group_nr: The scene group to sync
        """
        msg = self.construct_message('{"cmdId":' + str(Command.SYN_SCENE.value) +
                                     ',"sence_group":' + str(group_nr) + ',"answer_content":"","scene_content":""}')
        logging.info(f"sync scenes, group {group_nr}")
        await self.send_data(msg)

    async def sync_devices(self):
        """
        Sends a sync devices command to the K1
        """
        msg = self.construct_message('{"cmdId":' + str(Command.GET_ALL_EQUIPMENT_STATUS.value) + ',"device_status":""}')
        logging.info("sync devices")
        await self.send_data(msg)

    async def get_device_names(self):
        """
        Sends a get device names command to the K1
        """
        msg = self.construct_message('{"cmdId":' + str(Command.GET_DEVICE_NAME.value) + ',"device_ID":0}')
        await self.send_data(msg)

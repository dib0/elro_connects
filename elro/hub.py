import logging
import json
import socket
from threading import Thread

from elro.command import Command
from elro.device import DeviceDict, Device
from elro.utils import get_string_from_ascii


class Hub:
    APP_ID = '0'
    CTRL_KEY = '0'

    def __init__(self, ip, port, id):
        self.ip = ip
        self.port = port
        self.id = id

        self.devices = DeviceDict(lambda id: Device(id))

        self.msg_id = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receive_thread = Thread(target=self.receive_data)

    def connect(self):
        self.send_data('IOT_KEY?' + self.id)
        self.receive_thread.start()

        msg = self.construct_message('{"cmdId":' + str(Command.SYN_DEVICE_STATUS) + ',"device_status":""}')
        self.send_data(msg)

    def construct_message(self, data):
        self.msg_id += 1

        result = '{"msgId":' + str(self.msg_id) + \
                 ',"action":"appSend","params":{"devTid":"' + \
                 self.id + '","ctrlKey":"' + Hub.CTRL_KEY + '","appTid":"' + Hub.APP_ID + '","data":' + data + '}}'
        return result

    def send_data(self, data):
        self.sock.sendto(bytes(data, "utf-8"),
                         (self.ip, self.port))

    def receive_data(self):
        while True:
            data, server = self.sock.recvfrom(4096)

            reply = str(data)[2:-1]
            if reply.endswith('\\n'):
                reply = reply[:-2]
            if reply.endswith('\\r'):
                reply = reply[:-2]

            logging.debug('Received data: ' + reply)

            if reply.startswith('{') and reply != "{ST_answer_OK}":
                msg = json.loads(reply)
                dat = msg["params"]

                self.handle_command(dat)

                # Send reply
                self.send_data('APP_answer_OK')

    def handle_command(self, data):
        if data["data"]["cmdId"] == Command.DEVICE_STATUS_UPDATE:
            if data["data"]["device_name"] == "STATUES":
                return

            # set device ID
            d_id = data["data"]["device_ID"]
            dev = self.devices[d_id]
            dev.device_type = data["data"]["device_name"]

            # set battery status
            batt = int(data["data"]["device_status"][2:4], 16)
            dev.battery_level = batt

            dev.device_state = "Unknown"
            if data["data"]["device_name"] == "0101":  # Door/window sensor opened/closed
                if data["data"]["device_status"][4:-2] == "55":
                    logging.debug("Door/window id " + str(d_id) + " open!")
                    dev.device_state = "Open"
                elif data["data"]["device_status"][4:-2] == "AA":
                    logging.debug("Door/window id " + str(d_id) + " closed!")
                    dev.device_state = "Closed"
            else:  # Other sensors
                if data["data"]["device_status"][4:-2] == "BB":
                    dev.device_state = "Alarm"
                elif data["data"]["device_status"][4:-2] == "AA":
                    dev.device_state = "Normal"

        elif data["data"]["cmdId"] == Command.DEVICE_ALARM_TRIGGER:
            d_id = int(data["data"]["answer_content"][6:10], 16)
            dev = self.devices[d_id]
            logging.debug("ALARM!! Device_id " + str(d_id) + "(" + dev.name + ")")

        elif data["data"]["cmdId"] == Command.DEVICE_NAME_REPLY:
            answer = data["data"]["answer_content"]
            if answer == "NAME_OVER":
                return

            d_id = int(answer[0:4], 16)
            name_val = get_string_from_ascii(answer[4:])

            dev = self.devices[d_id]
            dev.name = name_val

    def sync_scenes(self, group_nr):
        msg = self.construct_message('{"cmdId":' + str(Command.SYN_SCENE) +
                                     ',"sence_group":' + str(group_nr) + ',"answer_content":"","scene_content":""}')
        self.send_data(msg)

    def sync_devices(self):
        msg = self.construct_message('{"cmdId":' + str(Command.GET_ALL_EQUIPMENT_STATUS) + ',"device_status":""}')
        self.send_data(msg)

    def get_device_names(self):
        msg = self.construct_message('{"cmdId":' + str(Command.GET_DEVICE_NAME) + ',"device_ID":0}')
        self.send_data(msg)

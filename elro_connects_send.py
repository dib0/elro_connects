import socket, time, json
from threading import Thread
from time import sleep
from elro_const import const
from elro_coder_util import coder_utils
from elro_device import device

MSG_ID = 0
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
DEVICES = []


def get_device(id):
    global DEVICES

    for dev in DEVICES:
        if dev.id == id:
            return dev
    
    dev = device()
    dev.id = id
    DEVICES.append(dev)
    return dev


def handle_command(data):
    global DEVICES

    if data["data"]["cmdId"] == const.DEVICE_STATUS_UPDATE:
        if data["data"]["device_name"] == "STATUES":
            return

        # set device ID
        d_id = data["data"]["device_ID"]
        dev = get_device(d_id)
        dev.device_type = data["data"]["device_name"]

        # set battery status
        batt = int(data["data"]["device_status"][2:4], 16)
        dev.battery_level = batt

        dev.device_state = "Unknown"
        if data["data"]["device_name"] == "0101": # Door/window sensor opened/closed
            if data["data"]["device_status"][4:-2] == "55":
                debug_output("Door/window id " + str(d_id) + " open!")
                dev.device_state = "Open"
            elif data["data"]["device_status"][4:-2] == "AA":
                debug_output("Door/window id " + str(d_id) + " closed!")
                dev.device_state = "Closed"
        else: # Other sensors
            if data["data"]["device_status"][4:-2] == "BB":
                dev.device_state = "Alarm"
            elif data["data"]["device_status"][4:-2] == "AA":
                dev.device_state = "Normal"
    
    elif data["data"]["cmdId"] == const.DEVICE_ALARM_TRIGGER:
        d_id = int(data["data"]["answer_content"][6:10], 16)
        dev = get_device(d_id)
        debug_output("ALARM!! Device_id " + str(d_id) + "(" + dev.name + ")")
    
    elif data["data"]["cmdId"] == const.DEVICE_NAME_REPLY:
        answer = data["data"]["answer_content"]
        if answer == "NAME_OVER":
            return

        d_id = int(answer[0:4], 16)
        name_val = coder_utils.getStringFromAscii(answer[4:])

        dev = get_device(d_id)
        dev.name = name_val


def send_data(data):
    global SOCK

    SOCK.sendto(bytes(data, "utf-8"), (const.SERVER_IP, const.SERVER_PORT))


def debug_output(txt):
    if const.DEBUG_SCRIPT:
        print(time.strftime("%Y-%m-%d %H:%M") + ' ' + txt)


def receive_data():
    global SOCK

    while True:
        data, server = SOCK.recvfrom(4096)

        reply = str(data)[2:-1] 
        if reply.endswith('\\n'):
            reply = reply[:-2]
        if reply.endswith('\\r'):
            reply = reply[:-2]

        debug_output('Received data: ' + reply)

        if reply.startswith('{') and reply != "{ST_answer_OK}":
            msg = json.loads(reply)
            dat = msg["params"]

            handle_command(dat)

            # Send reply
            send_data('APP_answer_OK')


def construct_message(data):
    global MSG_ID
    MSG_ID += 1

    result = '{"msgId":' + str(MSG_ID) + ',"action":"appSend","params":{"devTid":"' + const.DEVICE_ID + '","ctrlKey":"' + const.CTRL_KEY + '","appTid":"' + const.APP_ID + '","data":' + data + '}}'
    return result


def start_connection():
    # Send initial text
    send_data('IOT_KEY?' + const.DEVICE_ID)
    thread = Thread(target = receive_data)
    thread.start()

    msg = construct_message('{"cmdId":' + str(const.SYN_DEVICE_STATUS) + ',"device_status":""}')
    send_data(msg)


def sync_scenes(groupnr):
    msg = construct_message('{"cmdId":' + str(const.SYN_SCENE) + ',"sence_group":' + str(groupnr) + ',"answer_content":"","scene_content":""}')
    send_data(msg)


def sync_devices():
    msg = construct_message('{"cmdId":' + str(const.GET_ALL_EQUIPMENT_STATUS) + ',"device_status":""}')
    send_data(msg)


def get_device_names():
    msg = construct_message('{"cmdId":' + str(const.GET_DEVICE_NAME) + ',"device_ID":0}')
    send_data(msg)


def test_device_alarm(dev):
    debug_output("Testing alarm for " + dev.name)
    payload = "BB000000"
    if dev.device_type == device_type.FIRE_ALARM:
        payload = "17000000"

    msg = construct_message('{"cmdId":' + str(const.EQUIPMENT_CONTROL) + ',"device_ID":' + str(deviceid) + ',"device_status":"' + payload + '"}')
    send_data(msg)


# Main script loop
start_connection()
sync_scenes(0) # 0 is the first/default group
get_device_names()

# Main loop, keep updating every 30 seconds. Keeps 'connection' alive in order 
# to receive alarms/events
while True:
    sleep(30) # sleep first to handle the sync scenes and device names
    sync_devices()

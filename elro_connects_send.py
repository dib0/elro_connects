import socket, time, json
from threading import Thread
from time import sleep
from elro_const import const
from elro_coder_util import coder_utils

MSG_ID = 0
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def handle_command(data):
    if data["data"]["cmdId"] == 19:
        if data["data"]["device_name"] == "0101": # Door/window sensor opened/closed
            if data["data"]["device_status"][4:-2] == "55":
                print("Door/window id " + str(data["data"]["device_ID"]) + " open!")
            elif data["data"]["device_status"][4:-2] == "AA":
                print("Door/window id " + str(data["data"]["device_ID"]) + " closed!")
    elif data["data"]["cmdId"] == 25:
        print("ALARM!!")


def send_data(data):
    global SOCK

    SOCK.sendto(bytes(data, "utf-8"), (const.SERVER_IP, const.SERVER_PORT))


def receive_data():
    global SOCK

    while True:
        data, server = SOCK.recvfrom(4096)

        reply = str(data)[2:-1] 
        if reply.endswith('\\n'):
            reply = reply[:-2]
        if reply.endswith('\\r'):
            reply = reply[:-2]

        if const.DEBUG_SCRIPT:
            print(time.strftime("%Y-%m-%d %H:%M") + ' Received data: ' + reply)

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


def test_device_alarm(deviceid):
    #payload = "17000000" # For Firealarm
    payload = "BB000000"
    msg = construct_message('{"cmdId":' + str(const.EQUIPMENT_CONTROL) + ',"device_ID":' + str(deviceid) + ',"device_status":"' + payload + '"}')
    send_data(msg)


# Main script loop
start_connection()
sync_scenes(0) # 0 is the first/default group
#test_device_alarm(2)

# Main loop, keep updating every 30 seconds. Keeps 'connection' alive in order 
# to receive alarms/events
while True:
    sync_devices()
    sleep(30)


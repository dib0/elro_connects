# Elro connects protocol

## Connection

Send the device key `IOT_KEY?ST_xxxxxxxxxxxx` to the host and see if it responds with `NAME:ST_xxxxxxxxxxxx`. If this is the case then the connection is established.

After the initial connection message all following communication uses the json format. 

When the connection is first established we go on to send an initial [`SYN_DEVICE_STATUS`](#syn_device_status), [`SYN_SCENE`](#syn_scene), and [`GET_DEVICE_NAME`](#get_device_name) command.

## Processing loop

After being connected a [`GET_ALL_EQUIPMENT_STATUS`](#get_all_equipment_status) and [`GET_DEVICE_NAME`](#get_device_name) get send to the connector every 30 seconds.

## COMMANDS

Corresponding command ids can be found under [`elro/command.py`](elro/command.py).

### Send commands

Example of command message format

```
{"msgId": 1, "action": "appSend", "params": {"devTid": "ST_xxxxxxxxxxxx", "ctrlKey": "0", "appTid": "0", "data": {"cmdId": 15, "device_status": ""}}}
```

#### SYN_DEVICE_STATUS

#### SYN_SCENE

#### GET_DEVICE_NAME

Request the name of a device by passing `device_ID`. If this id is `0` then all names are requested. This command will be responded by [`DEVICE_NAME_REPLY`](#device_name_reply).

#### GET_ALL_EQUIPMENT_STATUS

Calls the connector to check for status updates which responds with a [`DEVICE_STATUS_UPDATE`](#device_status_update) command.


### Received commands

Example of received command message format

```json
{"msgId": 2, "action": "devSend", "params": { "devTid": "ST_xxxxxxxxxxxx", "appTid": [], "data": { "cmdId": 19, "device_ID": 65535, "device_name": "STATUES", "device_status": "OVER" }}}
```

Each received command message is replied to by `APP_answer_OK` to confirm to the hub that the message was received.

#### DEVICE_STATUS_UPDATE

In case there are no device updated this will be
```json
{"cmdId": 19, "device_ID": 65535, "device_name": "STATUES", "device_status": "OVER"}
```

otherwise a message containing the device info is received for each changed device

```json
{"cmdId": 19, "device_ID": 3, "device_name": "0013", "device_status": "0464AAFF"}
```

Here the `device_name` is actually the [type of device](#device-types).

The `device_status` is the devices info which can be split up in following pieces.

|    04   |          64          |           AA           |    FF   |
|---------|----------------------|------------------------|---------|
| Unknown | Battery as hex value | Device specific status | Unknown |

#### DEVICE_NAME_REPLY

```json
{"cmdId": 17, "answer_content": "000140404040404040404b69746368656e24"}
```

After requesting device names using [`GET_DEVICE_NAME`](#get_device_name) this reply will be send for each device. Here the information will be found under `answer_content`. This contains the device id in the first 4 characters and the name encoded as hexadecimal in the rest. Leading whitespace is displayed as `@` and the name is closed with a `$`. After the last name reply is send a final reply is send with `NAME_OVER`.

Example reponse data: `000140404040404040404b69746368656e24`.

|  Id  | Device name                      |
|------|----------------------------------|
| 0001 | 40404040404040404b69746368656e24 |
|    1 |                 @@@@@@@@Kitchen$ |

#### DEVICE_ALARM_TRIGGER

```json
{"cmdId": 25, "answer_content": "000BAD00030013046419A551EA"}
```

Received when a device alarm goes of. The `answer_content` contains the device id.

| 000BAD  |   0003    | 0013046419A551EA |
|---------|-----------|------------------|
| Unknown | Device id | Unknown          |


#### SCENE_STATUS_UPDATE


## Device types

Following types are currently known:

| Device type        |  Id  | Implementation |
|--------------------|------|----------------|
| CO_ALARM           | 0000 | AlarmSensor    |
| WATER_ALARM        | 0004 | AlarmSensor    |
| HEAT_ALARM         | 0003 | AlarmSensor    |
| FIRE_ALARM         | 0005 | AlarmSensor    |
| DOOR_WINDOW_SENSOR | 0101 | WindowSensor   |


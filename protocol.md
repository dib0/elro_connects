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

```json
{"msgId": 1, "action": "appSend", "params": {"devTid": "ST_xxxxxxxxxxxx", "ctrlKey": "0", "appTid": "0", "data": {"cmdId": 15, "device_status": ""}}}
```

When a change is made, the hub will respond with the following json

```json
{"msgId" : 2, "action" : "devSend","params" : {"devTid" : "ST_xxxxxxxxxxxx","appTid" :  [],"data" : {"cmdId" : 11,"answer_yes_or_no" : 2 }}}
```

#### SYN_DEVICE_STATUS

#### SYN_SCENE

#### GET_DEVICE_NAME

#### MODIFY_EQUIPMENT_NAME

To change the name of the device, cmdId 5 can be used with the following json

```json
{"cmdId":5,"device_ID":1,"device_name":"40404040404040404b69746368656e2493AE"}
```

To change the the name of the device, leading whitespace is required as `@` and the name is closed with a `$`. The name to use needs to encoded as hexadecimal. The hexadecimal string needs a CRC and that is placed at the end of the device_name. The CRC is 4 characters long.

Example device_name data: `40404040404040404b69746368656e2493AE`.

| Device name                           |
|---------------------------------------:|
| 40404040404040404b69746368656e2493AE  |
|@@@@@@@@Kitchen$[CRC]|

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

|    04     |          64            |           AA             |    FF     |
|:---------:|:----------------------:|:------------------------:|:---------:|
| Unknown   | Battery as hex value   | Device specific status   | Unknown   |

#### DEVICE_NAME_REPLY

```json
{"cmdId": 17, "answer_content": "000140404040404040404b69746368656e24"}
```

After requesting device names using [`GET_DEVICE_NAME`](#get_device_name) this reply will be send for each device. Here the information will be found under `answer_content`. This contains the device id in the first 4 characters and the name encoded as hexadecimal in the rest. Leading whitespace is displayed as `@` and the name is closed with a `$`. After the last name reply is send a final reply is send with `NAME_OVER`.

Example reponse data: `000140404040404040404b69746368656e24`.

|  Id  | Device name                      |
|------:|----------------------------------:|
| 0001 | 40404040404040404b69746368656e24 |
|    1 |                 @@@@@@@@Kitchen$ |


#### DEVICE_ALARM_TRIGGER

```json
{"cmdId": 25, "answer_content": "000BAD00030013046419A551EA"}
```

Received when a device alarm goes of. The `answer_content` contains the device id.

| 000B    | AD   |   0003    | 0013        | 046419A5      | 51EA    |
|---------|------|-----------|-------------|---------------|---------|
| Unknown | Type | Device id | Device type | Device status | Unknown |

The Type can be AC or AD and has to do with how the data is parsed. At this moment only AD is supported.

#### SCENE_STATUS_UPDATE


## Device types

Following types are currently known:

| Device type        | Implementation |
|--------------------|----------------|
| CO_ALARM           | AlarmSensor    |
| WATER_ALARM        | AlarmSensor    |
| HEAT_ALARM         | AlarmSensor    |
| FIRE_ALARM         | AlarmSensor    |
| DOOR_WINDOW_SENSOR | WindowSensor   |


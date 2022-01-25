**NOTE**

ELRO Connects probably will also function on the BASE smart home gateway SWM188A and the SITERWELL GS198. Both have not been tested.

# ELRO Connects

The ELRO Connects uses a propriety protocol on the local network over UDP. This is the reversed engineered python implementation of the protocol.

The ERLO K1 connects SF40GA system allows you to connect fire alarms, heat alarms, CO alarms, water alarms and door/window sensors through a hub. The app uses an internet connection, but on the local network it is possible to communicate with the hub through a propriety UDP protocol.

The ELRO connects hub allows only one 'connection' at a time. So running this will discontinue sending data to the app and vice versa.

Features to expect:
* MQTT capabilites -- can connect to an MQTT broker and publishes messages on events
* CLI interface with parameters
* More pythonic implementation
* No threads, but async with trio

## Setup
Simply install via pip

    $ pip install .

## Usage

    usage: elro [-h] -k HOSTNAME -m MQTT_BROKER [-b BASE_TOPIC] [-i ID] [-a]

    required arguments:
        -k HOSTNAME, --hostname HOSTNAME
                                The hostname or ip of the K1 connector.
        -m MQTT_BROKER, --mqtt-broker MQTT_BROKER
                                The IP of the MQTT broker.
        -b BASE_TOPIC, --base-topic BASE_TOPIC
                                The base topic of the MQTT topic.

    optional arguments:
        -i ID, --id ID        The ID of the K1 connector (format is ST_xxxxxxxxxxxx).
        -a, --ha-autodiscover
                                Send the devices automatically to Home Assistant.


## MQTT

### Broker

The `MQTT_BROKER` uses the [MQTT URL scheme](https://github.com/mqtt/mqtt.github.io/wiki/URI-Scheme).

    {mqtt,ws}[s]://[username][:password]@host.domain[:port]

### Topics

You can set the base topic of all MQTT messages with the `-b` flag. Then this application will publish on

    [base_topic]/elro/[device_id]
    
There are two message types: regular status update, and alarm. A regular status update contains a JSON message with the following format. This will probably change in a future release to five different messages.

```JSON
{
    "name": "fire_alarm_living_room", 
    "device_name": "fire_alarm_living_room", 
    "id": 8, 
    "type": "0013", 
    "type_name": "FIRE_ALARM", 
    "state": "Normal", 
    "battery": 95
}
```

When the device has an alarm the payload is the same as above, but the state is set to `Alarm` or `Test Alarm`.

To initiate an action through MQTT, use the following topic

    [base_topic]/elro/[device_id]/set/[action_topic]

Use the following values on [action_topic]

#### device_status

The device_status is capable of handling 2 values:
* "test alarm" - Enable a test alarm
* "silence" - silence the test alarm

If silence is used to silence an alarm, you can only send this to [device_id] 0, and it will only silence the hub.

#### device_name

Provide a new name to rename your device to. This can be a maximum of 15 characters and consist of the following characters (the , is not allowed): a-z,A-Z, 0-9, ,-,_

## Supported Devices by ERLO K1 connects SF40GA
### Fire alarms
* Elro FZ5002R
### Heat alarms
* Elro FH3801R
### CO alarms
* Elro FC4801R
### Water alarms
* Elro FW3801R
### Window and Door sensors
* Elro SF40MA11

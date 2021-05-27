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

    usage: elro [-h] [-k HOSTNAME] [-i ID] [-m MQTT_BROKER] [-b BASE_TOPIC]
    
    optional arguments:
      -h, --help            show this help message and exit
      -k HOSTNAME, --hostname HOSTNAME
                            The hostname or ip of the K1 connector.
      -i ID, --id ID        The ID of the K1 connector (format is ST_xxxxxxxxxxxx).
      -m MQTT_BROKER, --mqtt-broker MQTT_BROKER
                            The IP of the MQTT broker.
      -b BASE_TOPIC, --base-topic BASE_TOPIC
                            The base topic of the MQTT topic.


## MQTT

### Broker

The `MQTT_BROKER` uses the [MQTT URL scheme](https://github.com/mqtt/mqtt.github.io/wiki/URI-Scheme).

    {mqtt,ws}[s]://[username][:password]@host.domain[:port]

### Topics

You can set the base topic of all MQTT messages with the `-b` flag. Then this application will publish on

    [base_topic]/elro/[device_name_or_id]
    
There are two message types: regular status update, and alarm. A regular status update contains a JSON message with the following format. This will probably change in a future release to five different messages.

    {"name": "fire_alarm_living_room", 
    "id": 8, 
    "type": "0013", 
    "state": "Normal", 
    "battery": 95}

The alarm message only contains the word `alarm`.

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

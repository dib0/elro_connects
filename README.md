# ELRO Connects
This is a fork of http://github.com/dib0/elro_connects with extended features:

* MQTT capabilites -- can connect to an MQTT broker and publishes messages on events
* Real CLI interface with parameters
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

## Original explanation
The ELRO Connects uses a propriety protocol on the local network over UDP. This is the reversed engineered python implementation of the protocol.

The ERLO connects system allows you to connect fire alarms, heat alarms, CO alarms, water alarms and door/window sensors through a hub. The app uses an internet connection, but on the local network it is possible to communicate with the hub through a propriety UDP protocol.

The ELRO connects hub allows only one 'connection' at a time. So running this will discontinue sending data to the app and vice versa.

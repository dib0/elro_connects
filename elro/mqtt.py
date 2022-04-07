import logging
import json
import re

import trio
from distmqtt.client import open_mqttclient
from distmqtt.mqtt.constants import QOS_1

from elro.validation import ip_address, hostname


class MQTTPublisher:
    """
    A MQTTPublisher listens to all hub events and publishes messages to an MQTT broker accordingly
    """
    def __init__(self, broker_host, ha_autodiscover, base_topic=None):
        """
        Constructor
        :param broker_host: The MQTT broker host or ip
        :param ha_autodiscover: If true, new devices will be automatically discovered by Home Assistant
        :param base_topic: The base topic to publish under, i.e., the publisher publishes messages under
                           <base topic>/elro/<device name or id>
        """
        if (re.search(f"({ip_address}|{hostname})", broker_host) is None):
            raise TypeError(f"Invalid broker host ({broker_host})")

        if (re.search("^[/_\\-a-zA-Z0-9]*$", base_topic) is None):
            raise TypeError(f"Invalid base topic ({base_topic})")

        self.broker_host = broker_host
        if not self.broker_host.startswith("mqtt://"):
            self.broker_host = f"mqtt://{self.broker_host}"

        if base_topic is None:
            self.base_topic = ""
        else:
            self.base_topic = base_topic

        self.ha_autodiscover = ha_autodiscover

    def topic_name(self, device):
        """
        The topic name for a given device
        :param device: The device to get the topic name for
        """
        return f"{self.base_topic}/elro/{device.id}"

    async def device_alarm_task(self, device):
        """
        The main loop for handling alarm events
        :param device: The device to handle alarm events for.
        """
        while True:
            await self.handle_device_alarm(device)

    async def handle_device_alarm(self, device):
        """
        Listens for a device's alarm event and publishes a message on arrival.
        :param device: The device to listen to
        """
        await device.alarm.wait()
        async with open_mqttclient(uri=self.broker_host) as client:
            logging.info(f"Publish alarm on '{self.topic_name(device)}':\n"
                         f"{device.json.encode('utf-8')}")
            await client.publish(f'{self.topic_name(device)}',
                                 device.json.encode('utf-8'),
                                 QOS_1)

    async def device_update_task(self, device):
        """
        The main loop for handling device updates
        :param device: The device to listen to update events for
        """
        while True:
            await self.handle_device_update(device)

    async def handle_device_update(self, device):
        """
        Listens to a device's update events and publish a message on arrival
        :param device: The device to listen for updates for
        """
        await device.updated.wait()
        async with open_mqttclient(uri=self.broker_host) as client:
            logging.info(f"Publish update on '{self.topic_name(device)}':\n"
                         f"{device.json.encode('utf-8')}")
            await client.publish(f'{self.topic_name(device)}',
                                 device.json.encode('utf-8'),
                                 QOS_1)

    async def device_discovery_task(self, device):
        """
        The main handler for Home Assistant discovery
        :param device: The device to handle discover event for.
        """
        if self.ha_autodiscover is True and device.device_type != "DEL":
            await self.handle_device_discovery(device)

    async def handle_device_discovery(self, device):
        """
        Add new devices automatically in Home Assistant
        :param device: The device that will be added to Home Assistant
        """
        # https://www.home-assistant.io/docs/mqtt/discovery/
        # https://www.home-assistant.io/integrations/sensor.mqtt/
        async with open_mqttclient(uri=self.broker_host) as client:
            logging.info(f"Publish discovery on 'homeassistant/sensor/elro_k1/{device.id}/config'")
            await client.publish(
                f"homeassistant/sensor/elro_k1/{device.id}/config",
                json.dumps(
                {
                    "name": f"elro_k1_{device.id}",
                    "state_topic": f"{self.topic_name(device)}",
                    "value_template": "{{ value_json.state }}",
                    "json_attributes_topic": f"{self.topic_name(device)}",
                    "unique_id": f"elro_k1_device_{device.id}"
                }).encode('utf8'),
                QOS_1
            )

    async def device_message_task(self, hub):
        """
        The main loop for handling messages that will be sent to the device
        :param device: The device that will get the message
        """
        while True:
            await self.handle_device_messages(hub)

    async def handle_device_messages(self, hub):
        """
        The handler for the command topics
        :param hub: The hub to listen for devices
        """
        async with open_mqttclient(uri=self.broker_host) as client:
            logging.info(f"Subscribing to topic 'f{self.base_topic}/elro/[device_id]/set'")
            async with client.subscription(f"{self.base_topic}/elro/+/set", codec="utf8") as subscription:
                async for msg in subscription:
                    mqtt_message = msg.data.strip('\"')
                    logging.info(f"Got message '{mqtt_message}' on topic '{msg.topic}'")
                    topic_items = msg.topic.split('/')
                    device_index = None
                    for i in range(len(topic_items)):  # searching for the device index and the command
                        if topic_items[i].lower() == 'elro':
                            try:
                                device_index = int(topic_items[i+1])
                            except KeyError:
                                logging.error("Please provide the topic as [base_topic]/elro/[device_id]/set")
                            except ValueError:
                                logging.error("Please provide an integer for the device_index")
                            except Exception as error:
                                logging.error(f"Unknown error occured '{error}'")
                            break

                    if device_index is not None:
                        mqtt_message_json = None
                        try:
                            mqtt_message_json = json.loads(mqtt_message)
                        except Exception as error:
                            logging.error(f"Unable to parse MQTT JSON '{mqtt_message}' with error: '{error}'")
                        if mqtt_message_json is not None:
                            if "name" in mqtt_message_json and device_index != 0:
                                await hub.set_device_name(device_index, mqtt_message_json["name"])
                            elif "state" in mqtt_message_json:
                                if mqtt_message_json["state"].lower() == 'test alarm':
                                    await hub.set_device_state(device_index, '17')
                                elif mqtt_message_json["state"].lower() == 'silence' and device_index == 0:
                                    await hub.set_device_state(device_index, '00')
                                else:
                                    logging.warning(f"Unable to set state with incorrect message '{mqtt_message}' and/or topic '{msg.topic}'")
                            elif "permit_join" in mqtt_message_json and device_index == 0:
                                if mqtt_message_json["permit_join"] is True:
                                    await hub.permit_join_device()
                                elif mqtt_message_json["permit_join"] is False:
                                    await hub.permit_join_device_disable()
                            elif "remove" in mqtt_message_json and device_index != 0:
                                if mqtt_message_json["remove"] is True:
                                    await hub.remove_device(device_index, True)
                            elif "replace" in mqtt_message_json and device_index != 0:
                                if mqtt_message_json["replace"] is True:
                                    await hub.replace_device(device_index)
                                elif mqtt_message_json["replace"] is False:
                                    await hub.permit_join_device_disable()
                            else:
                                logging.warning(f"No action belongs to the MQTT message '{mqtt_message}' and/or topic '{msg.topic}'")
                    else:
                        logging.warning(f"Received message on topic '{msg.topic}', but there was no device index")

    async def handle_hub_events(self, hub):
        """
        Main loop to handle all device events
        :param hub: The hub to listen for devices
        """
        async with trio.open_nursery() as nursery:
            logging.info(f"Start listener for incoming mqtt")
            nursery.start_soon(self.device_message_task, hub)
            async for device_id in hub.new_device_receive_ch:
                logging.info(f"New device registered: {hub.devices[device_id]}")
                nursery.start_soon(self.device_update_task, hub.devices[device_id])
                nursery.start_soon(self.device_alarm_task, hub.devices[device_id])
                nursery.start_soon(self.device_discovery_task, hub.devices[device_id])

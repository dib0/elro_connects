import logging
import json

import trio
from distmqtt.client import open_mqttclient
from distmqtt.mqtt.constants import QOS_1
from valideer import accepts, Pattern

from elro.validation import ip_address, hostname


class MQTTPublisher:
    """
    A MQTTPublisher listens to all hub events and publishes messages to an MQTT broker accordingly
    """
    @accepts(broker_host=Pattern(f"({ip_address}|{hostname})"),
             base_topic=Pattern("^[/_\\-a-zA-Z0-9]*$"))
    def __init__(self, broker_host, ha_autodiscover, base_topic=None):
        """
        Constructor
        :param broker_host: The MQTT broker host or ip
        :param ha_autodiscover: If true, new devices will be automatically discovered by Home Assistant
        :param base_topic: The base topic to publish under, i.e., the publisher publishes messages under
                           <base topic>/elro/<device name or id>
        """
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
        if self.ha_autodiscover == True and device.device_type != "DEL":
            await self.handle_device_discovery(device)

    async def handle_device_discovery(self, device):
        """
        Add new devices automatically in Home Assistant
        :param device: The device that will be added to Home Assistant
        """
        #https://www.home-assistant.io/docs/mqtt/discovery/
        #https://www.home-assistant.io/integrations/sensor.mqtt/
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

    async def handle_hub_events(self, hub):
        """
        Main loop to handle all device events
        :param hub: The hub to listen for devices
        """
        async with trio.open_nursery() as nursery:
            async for device_id in hub.new_device_receive_ch:
                logging.info(f"New device registered: {hub.devices[device_id]}")
                nursery.start_soon(self.device_update_task, hub.devices[device_id])
                nursery.start_soon(self.device_alarm_task, hub.devices[device_id])
                nursery.start_soon(self.device_discovery_task, hub.devices[device_id])

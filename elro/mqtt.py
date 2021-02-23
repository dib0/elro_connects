import logging

import trio
from distmqtt.client import open_mqttclient
from distmqtt.mqtt.constants import QOS_1
from valideer import accepts, Pattern

from elro.validation import ip_address, hostname


class MQTTPublisher:
    @accepts(broker_host=Pattern(f"({ip_address}|{hostname})"),
             base_topic=Pattern("^[/_\\-a-zA-Z0-9]*$"))
    def __init__(self, broker_host, base_topic=None):
        self.broker_host = broker_host
        if not self.broker_host.startswith("mqtt://"):
            self.broker_host = f"mqtt://{self.broker_host}"

        if base_topic is None:
            self.base_topic = ""
        elif base_topic.startswith("/"):
            self.base_topic = base_topic
        else:
            self.base_topic = f"/{base_topic}"

    def topic_name(self, device):
        if device.name == "":
            last_hierarchy = device.id
        else:
            last_hierarchy = device.name

        return f"{self.base_topic}/elro/{last_hierarchy}"

    async def device_alarm_task(self, device):
        while True:
            await self.handle_device_alarm(device)

    async def handle_device_alarm(self, device):
        await device.alarm.wait()
        async with open_mqttclient(uri=self.broker_host) as client:
            logging.info(f"Publish on '{self.topic_name(device)}':\n"
                         f"alarm")
            await client.publish(f'{self.topic_name(device)}',
                                 b'alarm',
                                 QOS_1)

    async def device_update_task(self, device):
        while True:
            await self.handle_device_update(device)

    async def handle_device_update(self, device):
        await device.updated.wait()
        async with open_mqttclient(uri=self.broker_host) as client:
            logging.info(f"Publish on '{self.topic_name(device)}':\n"
                         f"{device.json.encode('utf-8')}")
            await client.publish(f'{self.topic_name(device)}',
                                 device.json.encode('utf-8'),
                                 QOS_1)

    async def handle_hub_events(self, hub):
        listening = []
        async with trio.open_nursery() as nursery:
            while True:
                await hub.new_device.wait()
                for device in hub.devices:
                    if device not in listening:
                        logging.info(f"New device registered: {hub.devices[device]}")
                        nursery.start_soon(self.device_update_task, hub.devices[device])
                        nursery.start_soon(self.handle_device_alarm, hub.devices[device])

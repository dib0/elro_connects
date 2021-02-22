import logging

import trio
from distmqtt.client import open_mqttclient
from distmqtt.mqtt.constants import QOS_1
from valideer import accepts, Pattern

from elro.validation import ip_address, hostname


class MQTTPublisher:
    @accepts(broker_host=Pattern(f"^mqtt://({ip_address})|({hostname})$"),
             base_topic=Pattern("^[a-zA-Z0-9\\-/]*$"))
    def __init__(self, broker_host, base_topic=None):
        self.broker_host = broker_host

        if base_topic is None:
            self.base_topic = ""
        elif base_topic.startswith("/"):
            self.base_topic = base_topic
        else:
            self.base_topic = f"/{base_topic}"

    async def device_alarm_task(self, device):
        while True:
            await self.handle_device_alarm(device)

    async def handle_device_alarm(self, device):
        await device.alarm.wait()
        async with open_mqttclient(uri=self.broker_host) as client:
            await client.publish(f'{self.base_topic}/elro/{device.name}',
                                 b'alarm',
                                 QOS_1)

    async def device_update_task(self, device):
        while True:
            await self.handle_device_update(device)

    async def handle_device_update(self, device):
        await device.updated.wait()
        async with open_mqttclient(uri=self.broker_host) as client:
            await client.publish(f'{self.base_topic}/elro/{device.name}',
                                 device.json.encode('utf-8'),
                                 QOS_1)

    async def handle_hub_events(self, hub):
        listening = []
        async with trio.open_nursery() as nursery:
            while True:
                await hub.new_device.wait()
                for device in hub.devices:
                    if device not in listening:
                        logging.inf(f"New device registered: {device}")
                        nursery.start_soon(self.device_update_task, hub.devices[device])
                        nursery.start_soon(self.handle_device_alarm, hub.devices[device])

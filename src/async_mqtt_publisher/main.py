import os
import asyncio
from typing import Optional, Tuple
from random import choice
from string import ascii_letters, digits
from uuid import uuid4
import logging

import aiohttp
from aiohttp.client_exceptions import ServerConnectionError

from .choices import Priorities
from .dataclasses import Settings, Queues, MQTTPublisherData


LETTERS_DIGITS = ascii_letters + digits
logger = logging.getLogger(__name__)


class MQTTPublisher:
    def __init__(self, aio_session: aiohttp.ClientSession):
        self.aio_session = aio_session
        self.settings = Settings(
            mqtt_login=os.getenv('MQTT_LOGIN', 'admin'),
            mqtt_password=os.getenv('MQTT_PASSWORD', 'public'),
            mqtt_host=os.getenv('MQTT_HOST'),
        )
        self.queues = Queues(
            high=asyncio.Queue(),
            middle=asyncio.Queue(),
            low=asyncio.Queue(),
        )
        asyncio.create_task(self.__task(priority=Priorities.high))
        asyncio.create_task(self.__task(priority=Priorities.high))
        asyncio.create_task(self.__task(priority=Priorities.high))
        asyncio.create_task(self.__task(priority=Priorities.high))
        asyncio.create_task(self.__task(priority=Priorities.middle))
        asyncio.create_task(self.__task(priority=Priorities.middle))
        asyncio.create_task(self.__task(priority=Priorities.middle))
        asyncio.create_task(self.__task(priority=Priorities.low))
        asyncio.create_task(self.__task(priority=Priorities.low))
        asyncio.create_task(self.__task(priority=Priorities.low))

    async def __publish(self, payload: str, qos: int = 0, topic: Optional[str] = None, topics: Optional[list] = None,
                        retain: bool = False) -> Tuple[dict, int]:
        data = {
            'payload': payload,
            'qos': qos,
            'retain': retain,
            'clientid': f'superAdmin{uuid4()}{"".join((choice(LETTERS_DIGITS) for _ in range(5)))}',
        }
        if topic:
            data['topic'] = topic
        elif topics:
            data['topics'] = ','.join(topics)

        out = {}
        async with self.aio_session.post(f'http://{self.settings.mqtt_host}:8081/api/v4/mqtt/publish', verify_ssl=False,
                                         auth=self.settings.mqtt_auth, json=data) as resp:
            if resp.status == 200:
                out = await resp.json()

        return out, resp.status

    async def __task(self, priority: Priorities):
        queue = self.queues.get_queue_by_priority(priority=priority)
        while True:
            data: MQTTPublisherData = await queue.get()
            try:
                resp, status = await self.__publish(
                    payload=data.payload, qos=data.qos, topic=data.topic, topics=data.topics)
                if status != 200:
                    logger.error(f"Problem send mqtt data. Status {status}")
            except ServerConnectionError as e:
                logger.exception(e)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.exception(e)

    async def publish_high(
            self, payload: str, qos: int = 0, topic: Optional[str] = None, topics: Optional[list] = None):
        await self.queues.high.put(MQTTPublisherData(topic=topic, topics=topics, payload=payload, qos=qos))

    async def publish_middle(
            self, payload: str, qos: int = 0, topic: Optional[str] = None, topics: Optional[list] = None):
        await self.queues.middle.put(MQTTPublisherData(topic=topic, topics=topics, payload=payload, qos=qos))

    async def publish_low(
            self, payload: str, qos: int = 0, topic: Optional[str] = None, topics: Optional[list] = None):
        await self.queues.low.put(MQTTPublisherData(topic=topic, topics=topics, payload=payload, qos=qos))
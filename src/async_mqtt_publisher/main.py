import os
import asyncio
from typing import Optional, Tuple, List
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
    def __init__(self):
        self.settings = Settings(
            mqtt_login=os.getenv('MQTT_LOGIN', 'admin'),
            mqtt_password=os.getenv('MQTT_PASSWORD', 'public'),
            mqtt_host=os.getenv('MQTT_HOST'),
            count_high=int(os.getenv('MQTT_COUNT_HIGH', 5)) or 1,
            count_middle=int(os.getenv('MQTT_COUNT_MIDDLE', 4)) or 1,
            count_low=int(os.getenv('MQTT_COUNT_LOW', 3)) or 1,
        )
        self.queues = Queues(
            high=asyncio.Queue(),
            middle=asyncio.Queue(),
            low=asyncio.Queue(),
        )
        self.__tasks = []
        for i in range(self.settings.count_high):
            self.__tasks.append(asyncio.create_task(self.__task(priority=Priorities.high, name=f"High priority: {i}")))
        for i in range(self.settings.count_middle):
            self.__tasks.append(asyncio.create_task(
                self.__task(priority=Priorities.middle, name=f"Middle priority: {i}")))
        for i in range(self.settings.count_low):
            self.__tasks.append(asyncio.create_task(self.__task(priority=Priorities.low, name=f"Low priority: {i}")))
        self.kwgs = {'ssl': False} if aiohttp.__version__ >= '3.8.0' else {'verify_ssl': False}

    async def __publish(self, aio_session: aiohttp.ClientSession, payload: str, qos: int = 0,
                        topic: Optional[str] = None, topics: Optional[list] = None,
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

        async with aio_session.post(
                f'http://{self.settings.mqtt_host}:8081/api/v4/mqtt/publish', auth=self.settings.mqtt_auth,
                json=data, **self.kwgs) as resp:
            if resp.status == 200:
                out = await resp.json()
            else:
                await self.publish_force(payload=payload, qos=qos, topic=topic, topics=topics)

        return out, resp.status

    async def __task(self, priority: Priorities, name: str):
        queue = self.queues.get_queue_by_priority(priority=priority)
        while True:
            async with aiohttp.ClientSession() as aio_session:
                data: Optional[MQTTPublisherData] = await queue.get()
                if not data:
                    logger.info(f"Task {name} was done!")
                    return
                try:
                    resp, status = await self.__publish(
                        aio_session=aio_session, payload=data.payload, qos=data.qos,
                        topic=data.topic, topics=data.topics)
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

    async def publish_force(self, payload: str, qos: int = 0, topic: Optional[str] = None,
                            topics: Optional[list] = None):
        async with aiohttp.ClientSession() as aio_session:
            try:
                resp, status = await self.__publish(
                    aio_session=aio_session, payload=payload, qos=qos, topic=topic, topics=topics)
            except ServerConnectionError as e:
                logger.exception(e)
                resp, status = {}, None
            return resp, status

    async def close(self):
        async def check_shutdown_tasks(tasks: List[asyncio.Task]):
            for task in tasks:
                if not task.done():
                    await asyncio.sleep(2)
                    await check_shutdown_tasks(tasks=[task])
            return

        for i in range(self.settings.count_high):
            await self.queues.high.put(None)
        for i in range(self.settings.count_middle):
            await self.queues.middle.put(None)
        for i in range(self.settings.count_low):
            await self.queues.low.put(None)

        await check_shutdown_tasks(tasks=self.__tasks)

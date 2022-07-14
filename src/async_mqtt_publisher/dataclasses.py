from dataclasses import dataclass
from asyncio import Queue
from typing import Optional, List

import aiohttp

from .choices import Priorities


@dataclass
class Settings:
    mqtt_login: str
    mqtt_password: str
    mqtt_host: str
    count_high: int
    count_middle: int
    count_low: int


    @property
    def mqtt_auth(self) -> aiohttp.BasicAuth:
        return aiohttp.BasicAuth(login=self.mqtt_login, password=self.mqtt_password)


@dataclass
class Queues:
    high: Queue
    middle: Queue
    low: Queue

    def get_queue_by_priority(self, priority: Priorities):
        mapping = {
            Priorities.high: self.high,
            Priorities.middle: self.middle,
            Priorities.low: self.low,
        }
        return mapping.get(priority)


@dataclass
class MQTTPublisherData:
    topic: Optional[str]
    topics: Optional[List[int]]
    payload: str
    qos: int

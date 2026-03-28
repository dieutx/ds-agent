import asyncio
import json
import random
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from typing import Any, Dict, List, Optional

from aiohttp_socks import ProxyConnector
from fake_useragent import UserAgent
from loguru import logger

from config.config import settings
from utils.exceptions import APIError


@dataclass
class AccountInfo:
    id: str
    username: str


@dataclass
class DiscordMessage:
    message_id: str
    channel_id: str
    content: str
    timestamp: datetime
    author_id: str
    author_username: str


@dataclass
class GuildInfo:
    id: str
    name: str


@dataclass
class GuildRoles:
    id: str
    name: str


@dataclass
class UserGuildRoles:
    id: str


@dataclass
class UserGuilds:
    id: str


class DiscordUserClient:
    BASE_URL = "https://discord.com/api/v9"

    def __init__(self, token: Optional[str] = None, proxy: Optional[str] = None):
        self.token = token
        self.proxy = proxy
        self.session: Optional[aiohttp.ClientSession] = None
        self._ua = UserAgent()

    async def __aenter__(self):
        headers = {
            "Authorization": f"{self.token}",
            "User-Agent": self._ua.random,
        }
        if self.proxy:
            connector = ProxyConnector.from_url("socks5://"+self.proxy)
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers=headers
            )
        else:
            self.session = aiohttp.ClientSession(
                headers=headers
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def get_account_info(self) -> AccountInfo | None:
        url = f"{self.BASE_URL}/users/@me"

        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                async with self.session.get(url) as resp:
                    data = await resp.json()

                    if resp.status != 200:
                        raise APIError(resp.status, data)

                    account_info = AccountInfo(data['id'], data['username'])

                    return account_info
            except APIError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {e.payload['message']}"
                )
                await asyncio.sleep(
                    random.randint(settings.SETTINGS.RETRY_DELAY[0], settings.SETTINGS.RETRY_DELAY[1])
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None

    async def get_channel_messages(
            self,
            channel_id: str,
            limit: int = 50
    ) -> list[DiscordMessage] | None:
        url = f"{self.BASE_URL}/channels/{channel_id}/messages"

        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                async with self.session.get(url, params={"limit": limit}) as resp:
                    data = await resp.json()

                    if resp.status != 200:
                        raise APIError(resp.status, data)

                    messages: List[DiscordMessage] = []
                    for msg_dict in data:
                        message_info = DiscordMessage(
                            message_id=msg_dict['id'],
                            channel_id=channel_id,
                            content=msg_dict['content'],
                            timestamp=msg_dict['timestamp'],
                            author_id=msg_dict['author']['id'],
                            author_username=msg_dict['author']['username']
                        )
                        messages.append(message_info)
                    return messages
            except APIError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {e.payload['message']}"
                )
                await asyncio.sleep(
                    random.randint(settings.SETTINGS.RETRY_DELAY[0], settings.SETTINGS.RETRY_DELAY[1])
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None

    async def send_message(
            self,
            channel_id: str,
            content: str,
    ) -> Dict[str, Any] | None:
        url = f"{self.BASE_URL}/channels/{channel_id}/messages"

        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                async with self.session.post(url, json={"content": content}) as resp:
                    data = await resp.json()

                    if resp.status != 200:
                        raise APIError(resp.status, data)
                    return data
            except APIError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {e.payload['message']}"
                )
                await asyncio.sleep(
                    random.randint(settings.SETTINGS.RETRY_DELAY[0], settings.SETTINGS.RETRY_DELAY[1])
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None


    async def send_media_message(
            self,
            channel_id: str,
            media_path: str,
    ) -> Dict[str, Any] | None:
        url = f"{self.BASE_URL}/channels/{channel_id}/messages"

        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                form = aiohttp.FormData()
                form.add_field(
                    name="payload_json",
                    value=json.dumps({}),
                    content_type="application/json"
                )

                with open(media_path, "rb") as f:
                    form.add_field(
                        name="files[0]",
                        value=f,
                        filename=media_path,
                        content_type="image/png"
                    )

                    async with self.session.post(url, data=form) as resp:
                        data = await resp.json()

                        if resp.status != 200:
                            raise APIError(resp.status, data)

                        return data
            except APIError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {e.payload['message']}"
                )
                await asyncio.sleep(
                    random.randint(settings.SETTINGS.RETRY_DELAY[0], settings.SETTINGS.RETRY_DELAY[1])
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None


    async def get_user_guilds(self, user_id: str) -> List[UserGuilds] | None:
        url = f"{self.BASE_URL}/users/{user_id}/profile"

        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                async with self.session.get(url) as resp:
                    data = await resp.json()

                    if resp.status != 200:
                        raise APIError(resp.status, data)

                    guilds: List[UserGuilds] = []
                    for guild in data['mutual_guilds']:
                        user_guild = UserGuilds(guild["id"])
                        guilds.append(user_guild)
                    return guilds
            except APIError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {e.payload['message']}"
                )
                await asyncio.sleep(
                    random.randint(settings.SETTINGS.RETRY_DELAY[0], settings.SETTINGS.RETRY_DELAY[1])
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None

    async def get_guild_info(self, guilds_id: str) -> GuildInfo | None:
        url = f"{self.BASE_URL}/guilds/{guilds_id}"

        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                async with self.session.get(url) as resp:
                    data = await resp.json()

                    if resp.status != 200:
                        raise APIError(resp.status, data)
                    guild_info = GuildInfo(data['id'], data['name'])
                    return guild_info
            except APIError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {e.payload['message']}"
                )
                await asyncio.sleep(
                    random.randint(settings.SETTINGS.RETRY_DELAY[0], settings.SETTINGS.RETRY_DELAY[1])
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None

    async def get_guild_roles(self, guilds_id: str) -> List[GuildRoles] | None:
        url = f"{self.BASE_URL}/guilds/{guilds_id}/roles"

        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                async with self.session.get(url) as resp:
                    data = await resp.json()

                    if resp.status != 200:
                        raise APIError(resp.status, data)

                    roles: List[GuildRoles] = []
                    for roles_dict in data:
                        role_info = GuildRoles(
                            id=roles_dict['id'],
                            name=roles_dict['name'],
                        )
                        roles.append(role_info)
                    return roles
            except APIError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {e.payload['message']}"
                )
                await asyncio.sleep(
                    random.randint(settings.SETTINGS.RETRY_DELAY[0], settings.SETTINGS.RETRY_DELAY[1])
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None

    async def get_user_roles_on_guild(self, guilds_id: str, user_id: str) -> List[UserGuildRoles] | None:
        url = f"{self.BASE_URL}/guilds/{guilds_id}/members/{user_id}"

        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                async with self.session.get(url) as resp:
                    data = await resp.json()

                    if resp.status != 200:
                        raise APIError(resp.status, data)

                    roles: List[UserGuildRoles] = []
                    for roles_dict in data["roles"]:
                        role_info = UserGuildRoles(
                            id=roles_dict
                        )
                        roles.append(role_info)
                    return roles
            except APIError as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {e.payload['message']}"
                )
                await asyncio.sleep(
                    random.randint(settings.SETTINGS.RETRY_DELAY[0], settings.SETTINGS.RETRY_DELAY[1])
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None

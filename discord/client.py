import asyncio
import json
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

import aiohttp
from aiohttp_socks import ProxyConnector
from fake_useragent import UserAgent
from loguru import logger

from config.config import settings
from utils.exceptions import APIError

T = TypeVar("T")


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
            connector = ProxyConnector.from_url("socks5://" + self.proxy)
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

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        handler: Callable[[aiohttp.ClientResponse], Any],
        **kwargs,
    ) -> Optional[Any]:
        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                async with self.session.request(method, url, **kwargs) as resp:
                    if resp.status == 429:
                        retry_after = float(resp.headers.get("Retry-After", 5))
                        logger.warning(
                            f"[{self.token[:8]}] Rate limited, waiting {retry_after:.1f}s"
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    data = await resp.json()

                    if resp.status != 200:
                        raise APIError(resp.status, data)

                    return handler(data)

            except APIError as e:
                msg = e.payload.get("message", str(e.payload)) if isinstance(e.payload, dict) else str(e.payload)
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {msg}"
                )
                await asyncio.sleep(
                    random.randint(
                        settings.SETTINGS.RETRY_DELAY[0],
                        settings.SETTINGS.RETRY_DELAY[1],
                    )
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None

    async def get_account_info(self) -> AccountInfo | None:
        url = f"{self.BASE_URL}/users/@me"
        return await self._request_with_retry(
            "GET", url,
            lambda data: AccountInfo(data["id"], data["username"]),
        )

    async def get_channel_messages(
        self,
        channel_id: str,
        limit: int = 50,
    ) -> list[DiscordMessage] | None:
        url = f"{self.BASE_URL}/channels/{channel_id}/messages"

        def parse(data):
            return [
                DiscordMessage(
                    message_id=msg["id"],
                    channel_id=channel_id,
                    content=msg["content"],
                    timestamp=msg["timestamp"],
                    author_id=msg["author"]["id"],
                    author_username=msg["author"]["username"],
                )
                for msg in data
            ]

        return await self._request_with_retry(
            "GET", url, parse, params={"limit": limit}
        )

    async def send_message(
        self,
        channel_id: str,
        content: str,
    ) -> Dict[str, Any] | None:
        url = f"{self.BASE_URL}/channels/{channel_id}/messages"
        return await self._request_with_retry(
            "POST", url, lambda data: data, json={"content": content}
        )

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
                    content_type="application/json",
                )

                with open(media_path, "rb") as f:
                    form.add_field(
                        name="files[0]",
                        value=f,
                        filename=media_path,
                        content_type="image/png",
                    )

                    async with self.session.post(url, data=form) as resp:
                        if resp.status == 429:
                            retry_after = float(resp.headers.get("Retry-After", 5))
                            logger.warning(
                                f"[{self.token[:8]}] Rate limited, waiting {retry_after:.1f}s"
                            )
                            await asyncio.sleep(retry_after)
                            continue

                        data = await resp.json()

                        if resp.status != 200:
                            raise APIError(resp.status, data)

                        return data
            except APIError as e:
                msg = e.payload.get("message", str(e.payload)) if isinstance(e.payload, dict) else str(e.payload)
                logger.warning(
                    f"Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {self.token[:8]}...: {msg}"
                )
                await asyncio.sleep(
                    random.randint(
                        settings.SETTINGS.RETRY_DELAY[0],
                        settings.SETTINGS.RETRY_DELAY[1],
                    )
                )

            except aiohttp.ClientError as e:
                logger.error(f"Error: {e}")

            except Exception as e:
                logger.error(f"Error: {e}")
        return None

    async def get_user_guilds(self, user_id: str) -> List[UserGuilds] | None:
        url = f"{self.BASE_URL}/users/{user_id}/profile"
        return await self._request_with_retry(
            "GET", url,
            lambda data: [UserGuilds(g["id"]) for g in data["mutual_guilds"]],
        )

    async def get_guild_info(self, guilds_id: str) -> GuildInfo | None:
        url = f"{self.BASE_URL}/guilds/{guilds_id}"
        return await self._request_with_retry(
            "GET", url,
            lambda data: GuildInfo(data["id"], data["name"]),
        )

    async def get_guild_roles(self, guilds_id: str) -> List[GuildRoles] | None:
        url = f"{self.BASE_URL}/guilds/{guilds_id}/roles"
        return await self._request_with_retry(
            "GET", url,
            lambda data: [GuildRoles(id=r["id"], name=r["name"]) for r in data],
        )

    async def get_user_roles_on_guild(self, guilds_id: str, user_id: str) -> List[UserGuildRoles] | None:
        url = f"{self.BASE_URL}/guilds/{guilds_id}/members/{user_id}"
        return await self._request_with_retry(
            "GET", url,
            lambda data: [UserGuildRoles(id=r) for r in data["roles"]],
        )

import asyncio
import csv
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

from loguru import logger

from config.config import settings, ACCOUNTS, PROXIES
from discord.client import DiscordUserClient


class TokenStatus(Enum):
    ACTIVE = "ACTIVE"
    INVALID = "INVALID"
    LOCKED = "LOCKED"
    QUARANTINED = "QUARANTINED"
    SPAMMER = "SPAMMER"
    SPAMMER_QUARANTINED = "SPAMMER_QUARANTINED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


@dataclass
class TokenInfo:
    token: str
    username: Optional[str] = None
    status: TokenStatus = TokenStatus.UNKNOWN
    user_id: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.now)

    @property
    def is_valid(self) -> bool:
        return self.status == TokenStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": self.token[:8] + "...",
            "username": self.username,
            "status": self.status.value,
            "user_id": self.user_id,
            "checked_at": self.checked_at.strftime("%d.%m.%Y %H:%M:%S"),
        }


class TokenChecker:
    FLAG_QUARANTINED = 17592186044416
    FLAG_SPAMMER = 1048576
    FLAG_SPAMMER_AND_QUARANTINED = FLAG_QUARANTINED + FLAG_SPAMMER

    def __init__(self):
        if settings.SETTINGS.USE_PROXY:
            pairs = list(zip(ACCOUNTS, PROXIES))
            if settings.SETTINGS.RANDOM_ACCOUNTS:
                random.shuffle(pairs)
            self.account_proxy_map: Dict[str, Optional[str]] = dict(pairs)
        else:
            self.account_proxy_map: Dict[str, Optional[str]] = {account: None for account in ACCOUNTS}

        self.results: List[TokenInfo] = []
        self.semaphore = asyncio.Semaphore(
            settings.SETTINGS.get("CHECK_CONCURRENCY", 10)
        )

    async def check_all(self) -> List[TokenInfo]:
        if not self.account_proxy_map:
            logger.error("No accounts (with proxies) found!")
            return []

        accounts = list(self.account_proxy_map.keys())
        logger.info(f"Starting token validation for {len(accounts)} accounts")

        tasks = [
            self._check_token_with_semaphore(token, idx)
            for idx, token in enumerate(accounts, 1)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        self.results = []
        for result in results:
            if isinstance(result, TokenInfo):
                self.results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Unexpected error during token check: {result}")

        logger.info(f"Token validation completed. Checked: {len(self.results)}")

        await self._save_results()

        return self.results

    async def _check_token_with_semaphore(self, token: str, index: int) -> TokenInfo:
        async with self.semaphore:
            return await self._check_token(token, index)

    async def _check_token(self, token: str, index: int) -> TokenInfo:
        token_info = TokenInfo(token=token)
        token_preview = f"{token[:8]}..."

        proxy = self.account_proxy_map.get(token)

        logger.debug(f"[{index}] Checking token: {token_preview}")

        for attempt in range(settings.SETTINGS.RETRY_COUNT):
            try:
                async with DiscordUserClient(token=token, proxy=proxy) as client:
                    account_data = await client.get_account_info()

                    token_info.user_id = account_data.id
                    token_info.username = account_data.username

                    flags_value = self._calculate_flags(account_data)

                    token_info.status = self._determine_status(flags_value)

                    logger.info(
                        f"[{index}] Token validated: {token_preview} | "
                        f"User: {token_info.username} | "
                        f"Status: {token_info.status.value}"
                    )

                    return token_info

            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)

                logger.warning(
                    f"[{index}] Attempt {attempt + 1}/{settings.SETTINGS.RETRY_COUNT} "
                    f"failed for {token_preview}: {error_type} - {error_msg}"
                )

                if "401" in error_msg or "Unauthorized" in error_msg:
                    token_info.status = TokenStatus.INVALID
                    return token_info

                elif "403" in error_msg or "Forbidden" in error_msg:
                    token_info.status = TokenStatus.LOCKED
                    return token_info

                if attempt < settings.SETTINGS.RETRY_COUNT - 1:
                    await asyncio.sleep(2 ** attempt)

        token_info.status = TokenStatus.ERROR
        logger.error(f"[{index}] All attempts failed for {token_preview}")

        return token_info

    @staticmethod
    def _calculate_flags(account_data: Any) -> int:
        try:
            flags = getattr(account_data, 'flags', 0) or 0
            public_flags = getattr(account_data, 'public_flags', 0) or 0
            return flags - public_flags
        except Exception as e:
            logger.warning(f"Error calculating flags: {e}")
            return 0

    def _determine_status(self, flags_value: int) -> TokenStatus:
        if flags_value == self.FLAG_QUARANTINED:
            return TokenStatus.QUARANTINED
        elif flags_value == self.FLAG_SPAMMER:
            return TokenStatus.SPAMMER
        elif flags_value == self.FLAG_SPAMMER_AND_QUARANTINED:
            return TokenStatus.SPAMMER_QUARANTINED
        else:
            return TokenStatus.ACTIVE

    async def _save_results(self) -> None:
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        csv_path = results_dir / f"token_check_{timestamp}.csv"

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'token', 'username', 'status', 'user_id', 'checked_at'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for info in self.results:
                writer.writerow(info.to_dict())

        active_tokens = [info.token for info in self.results if info.is_valid]
        if active_tokens:
            active_path = results_dir / f"active_tokens_{timestamp}.txt"
            active_path.write_text('\n'.join(active_tokens))
            logger.info(f"Saved {len(active_tokens)} active tokens to {active_path}")

        logger.info(f"Results saved to {csv_path}")

    def get_active_tokens(self) -> List[str]:
        return [info.token for info in self.results if info.is_valid]

    def get_statistics(self) -> Dict[str, int]:
        stats = {}
        for info in self.results:
            status = info.status.value
            stats[status] = stats.get(status, 0) + 1
        return stats


async def check_tokens() -> List[TokenInfo]:
    checker = TokenChecker()
    results = await checker.check_all()

    stats = checker.get_statistics()
    active_count = stats.get(TokenStatus.ACTIVE.value, 0)
    total_count = len(results)

    logger.info(
        f"Token check completed: {active_count}/{total_count} active tokens found"
    )

    return results
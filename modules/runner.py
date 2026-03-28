import asyncio
import random
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from loguru import logger

from config.config import settings, ACCOUNTS, PROXIES
from modules.sender import run_message_sender


@dataclass
class AccountConfig:
    token: str
    proxy: Optional[str] = None


class UnifiedRunner:
    def __init__(self, mode: str = "always_mode"):
        self.mode = mode

        if settings.SETTINGS.USE_PROXY:
            pairs = list(zip(ACCOUNTS, PROXIES))
            if settings.SETTINGS.RANDOM_ACCOUNTS:
                random.shuffle(pairs)
            self.account_proxy_map: Dict[str, Optional[str]] = dict(pairs)
        else:
            self.account_proxy_map: Dict[str, Optional[str]] = {account: None for account in ACCOUNTS}

        self.batch_size = settings.SETTINGS.BATCH_SIZE
        self.batch_delay = settings.SETTINGS.BATCH_DELAY
        self.intra_batch_delay = settings.SETTINGS.INTRA_BATCH_DELAY

    async def start(self):
        logger.info("Starting software...")

        if not self.account_proxy_map:
            logger.error("No accounts (with proxies) found!")
            return

        if not self._has_any_tasks():
            logger.error("No tasks found in configuration!")
            return

        accounts = list(self.account_proxy_map.keys())
        account_batches = [
            accounts[i:i + self.batch_size]
            for i in range(0, len(accounts), self.batch_size)
        ]

        logger.info(f"Split accounts into {len(account_batches)} batches")

        all_tasks = []
        for batch_idx, account_batch in enumerate(account_batches):
            if batch_idx > 0:
                variance = settings.SETTINGS.get("BATCH_DELAY_VARIANCE", 0.2)
                delay = random.uniform(
                    self.batch_delay * (1 - variance),
                    self.batch_delay * (1 + variance),
                )
                logger.info(f"Waiting {delay:.1f}s before batch {batch_idx + 1}/{len(account_batches)}...")
                await asyncio.sleep(delay)

            logger.info(f"Starting batch {batch_idx + 1}/{len(account_batches)} with {len(account_batch)} accounts")

            batch_tasks = await self._start_batch(account_batch, batch_idx)
            all_tasks.extend(batch_tasks)

        try:
            await asyncio.gather(*all_tasks)
        except (KeyboardInterrupt, SystemExit):
            logger.error("Stopping all tasks...")
            for task in all_tasks:
                task.cancel()
            await asyncio.gather(*all_tasks, return_exceptions=True)

    def _has_any_tasks(self) -> bool:
        return self._has_tasks_of_type(['1', '2', '3'])

    async def _start_batch(self, account_batch: List[str], batch_idx: int) -> List[asyncio.Task]:
        batch_tasks = []

        for acc_idx, account in enumerate(account_batch):
            intra_delay = random.uniform(*self.intra_batch_delay)

            task = asyncio.create_task(
                self._run_account(
                    account=account,
                    account_id=f"batch: {batch_idx + 1} | account: {account[:8]}...:{acc_idx + 1}",
                    delay=intra_delay
                )
            )
            batch_tasks.append(task)

            await asyncio.sleep(0.1)

        return batch_tasks

    async def _run_account(self, account: str, account_id: str, delay: float):
        if delay > 0:
            logger.info(f"[{account_id}] Starting in delay {delay:.1f}s...")
            await asyncio.sleep(delay)

        if settings.SETTINGS.USE_PROXY:
            proxy = self.account_proxy_map.get(account)
            logger.info(f"[{account_id}] Account {account[:12]}... started with proxy={proxy}")
        else:
            proxy = None
            logger.info(f"[{account_id}] Account {account[:12]}... started")

        try:
            await run_message_sender(mode=self.mode, account=account, proxy=proxy)
        except Exception as e:
            logger.error(f"[{account_id}] Error: {e}]")
        finally:
            logger.info(f"[{account_id}] Account finished")

    async def _run_messages_for_account(self, account: str, account_id: str):
        logger.info(f"[{account_id}] Starting message sender")
        await run_message_sender(mode=self.mode, account=account)

    @staticmethod
    def _has_tasks_of_type(message_types) -> bool:
        if isinstance(message_types, str):
            message_types = [message_types]

        for server_name, server_config in settings.SERVERS.items():
            if not server_config.get('ENABLED', False):
                continue

            for chat_config in server_config.get('CHATS', []):
                if chat_config.get('message_type') in message_types:
                    return True

        return False


async def run_unified(mode: str = "always_mode"):
    if mode not in ["always_mode", "one_time_mode"]:
        raise ValueError(f"Invalid mode: {mode}. Use 'always_mode' or 'one_time_mode'")

    runner = UnifiedRunner(mode=mode)
    await runner.start()

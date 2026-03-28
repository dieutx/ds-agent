from pathlib import Path

from dynaconf import Dynaconf
from loguru import logger

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=[
        "config.yaml",
    ],
    environments=True,
    load_dotenv=True,
    env_switcher="ENV_FOR_DYNACONF",
    merge_enabled=True,
)


def _load_lines(filepath: str) -> list[str]:
    path = Path(filepath)
    if not path.exists():
        logger.warning(f"{filepath} not found, using empty list")
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


ACCOUNTS = _load_lines("accounts.txt")
PROXIES = _load_lines("proxy.txt")

import asyncio
import sys

import questionary
from questionary import Choice

from logo import print_startup_window
from modules.checker import check_tokens
from modules.runner import run_unified


def get_module():
    result = questionary.select(
        "Available options:",
        choices=[
            Choice("1) Always-On Mode", "always_mode"),
            Choice("2) One-Time Mode", "one_time_mode"),
            Choice("3) Token Checker", "token_checker"),
            Choice("4) Exit", "exit"),
        ],
        qmark="⚙️ ",
        pointer="✅ "
    ).ask()
    if result == "exit":
        print("\n❤️ Subscribe to me – https://t.me/sybilwave")
        sys.exit()
    return result


async def main(module: str):
    if module in ["always_mode", "one_time_mode"]:
        await run_unified(module)
    elif module == "token_checker":
        await check_tokens()


if __name__ == "__main__":
    print_startup_window()
    module = get_module()

    try:
        asyncio.run(main(module))
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
        print("❤️ Subscribe to me – https://t.me/sybilwave")
        sys.exit(0)
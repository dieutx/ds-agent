#!/usr/bin/env python3
"""Post an image + caption to a Discord channel via user token and HTTP proxy."""
import argparse
import json
import sys
from pathlib import Path

import httpx


def post_meme(token: str, channel_id: str, proxy: str, image_path: str, caption: str):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"

    headers = {
        "Authorization": token,
    }

    filename = Path(image_path).name
    mime = "image/png" if filename.endswith(".png") else "image/jpeg"

    with open(image_path, "rb") as f:
        files = {"files[0]": (filename, f, mime)}
        data = {"payload_json": json.dumps({"content": caption})}

        client_kwargs = {"timeout": 30, "headers": headers}
        if proxy:
            client_kwargs["proxy"] = proxy
        with httpx.Client(**client_kwargs) as client:
            resp = client.post(url, data=data, files=files)

    if resp.status_code == 200:
        msg = resp.json()
        print(f"Posted successfully! Message ID: {msg['id']}")
    elif resp.status_code == 429:
        retry_after = resp.json().get("retry_after", "?")
        print(f"Rate limited. Retry after {retry_after}s")
        sys.exit(1)
    else:
        print(f"Failed with status {resp.status_code}: {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--image", required=True)
    parser.add_argument("--caption", required=True)
    args = parser.parse_args()

    post_meme(args.token, args.channel, args.proxy, args.image, args.caption)

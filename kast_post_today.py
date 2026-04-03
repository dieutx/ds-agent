#!/usr/bin/env python3
"""Generate 1-2 Kast memes with random timing and post to Discord + report to Telegram."""

import asyncio
import random
import time
import subprocess
import sys
import os
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

# Load .env
env_file = SCRIPT_DIR / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
KAST_CHANNEL = os.environ.get("KAST_CHANNEL_ID", "1313523536400486400")
PROXY = os.environ["PROXY"]
TG_BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]
HERMES = "/root/.local/bin/hermes"
MEDIA_DIR = SCRIPT_DIR / "media"
MEDIA_DIR.mkdir(exist_ok=True)

TOPICS = [
    "me flexing my Kast card at the store while everyone else fumbles with bank apps",
    "traditional bank: please wait 2-5 business days vs Kast: money sent, done",
    "me when I get my Kast card in the mail — tap to pay like a boss, stonks energy",
    "normal people phone: 10 different finance apps vs Kast: everything in one place",
    "the Kast Pengu mascot conquering the world of payments one country at a time",
    "bank tellers when they see you paying with a Kast crypto card at the grocery store",
    "Pengu holding a Kast card like its the infinity gauntlet of finance",
    "friends still using slow bank transfers while I already paid with Kast and left",
    "traveling abroad with 5 different cards vs just one Kast card that works globally",
    "when the cashier says they accept Visa and you pull out the Kast card with lightning design",
    "old finance: fees everywhere, slow transfers, hold music vs Kast: just works",
    "the whole squad when someone pulls out the black Kast card at dinner",
    "me checking my Kast app at 3am because the UI is just too clean",
]

STYLES = [
    "Multi-panel comparison meme (2-4 panels): left side shows frustrating old way, right side shows Kast solving it. Include the Kast logo (white K on black) or a dark premium-looking Kast Visa card with lightning design. Clean modern look.",
    "Reaction meme with a cute blue penguin mascot (Pengu — Kast's mascot). The penguin is small, round, blue and white with a happy face. Show Pengu doing something confident or funny related to payments/finance. Polished illustration style.",
    "Product showcase meme: a sleek dark Kast Visa card (black card, white K logo, lightning bolt design) shown in a cool context — someone flexing it, tapping to pay, or holding it dramatically. Cinematic/premium feel with dark blue/purple lighting.",
    "Before/After or expectation vs reality meme about payments. Left: old frustrating way. Right: clean Kast solution. Include the Kast card or Kast logo. Modern clean design.",
    "Classic meme template (Drake, Distracted Boyfriend, Expanding Brain, Stonks guy) but themed around Kast card, Pengu mascot, or Kast payments. Short punchy text, max 5-8 words per section.",
]


def generate_meme(meme_path: str, topic: str, style: str) -> bool:
    """Generate a meme image using Hermes. Returns True on success."""
    prompt = f"""Create a meme image for the Kast (kast.xyz) Discord community.

TOPIC: {topic}

STYLE: {style}

KEY BRAND ELEMENTS (include at least one):
- Kast card: a sleek dark/black Visa or Mastercard card with a white K logo and blue lightning bolt design
- Pengu: Kast's cute round blue-and-white penguin mascot with a happy/confident expression
- Kast logo: white K on black square background

RULES:
- Text must be SHORT (max 5-8 words per text area)
- High quality, polished look — NOT low-effort Impact font memes
- Must feel like a real community member made it, not a brand account
- NEVER mention AI, bots, Claude, Hermes, or automation
- The vibe is: premium fintech meets crypto culture meets cute mascot

Save to {meme_path}."""

    env = os.environ.copy()
    env["HOME"] = "/home/hermes_chatgpt"

    try:
        result = subprocess.run(
            [HERMES, "chat", "-q", prompt, "-Q"],
            env=env, capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("  Hermes timed out (300s)")
    return Path(meme_path).exists() and Path(meme_path).stat().st_size > 1000


def generate_caption(topic: str) -> str:
    """Generate a short caption using Hermes."""
    prompt = f"Write a very short casual Discord message (max 8 words) to post with a Kast meme about: {topic}. Sound like a real Kast community member — casual, hype about the product, maybe mention the card or Pengu. No hashtags. No AI mention. Just the message, nothing else."

    env = os.environ.copy()
    env["HOME"] = "/home/hermes_chatgpt"

    try:
        result = subprocess.run(
            [HERMES, "chat", "-q", prompt, "-Q"],
            env=env, capture_output=True, text=True, timeout=120,
        )
        lines = [
            l.strip() for l in result.stdout.splitlines()
            if l.strip()
            and "session_id" not in l
            and "Copilot" not in l
            and "copilot" not in l
            and "token" not in l.lower()
            and not l.startswith("╭")
            and not l.startswith("╰")
            and "ghp_" not in l
            and "OAuth" not in l
        ]
        if lines:
            return lines[-1]
    except Exception:
        pass
    return "kast card hits different fr 🐧"


def post_to_discord(image_path: str, caption: str) -> bool:
    """Post meme to Discord. Tries with proxy first, falls back to direct."""
    for use_proxy in [True, False]:
        cmd = [
            sys.executable, str(SCRIPT_DIR / "post_meme.py"),
            "--token", DISCORD_TOKEN,
            "--channel", KAST_CHANNEL,
            "--image", image_path,
            "--caption", caption,
        ]
        if use_proxy and PROXY:
            cmd.extend(["--proxy", PROXY])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            print(f"  Discord {'(proxy)' if use_proxy else '(direct)'}: {result.stdout.strip()}")
            if result.returncode == 0 and "successfully" in result.stdout.lower():
                return True
            if not use_proxy:
                print(f"  Discord error: {result.stderr.strip()[:200]}")
        except subprocess.TimeoutExpired:
            print(f"  Discord {'(proxy)' if use_proxy else '(direct)'}: timed out")
        if use_proxy:
            print("  Proxy failed, trying direct...")
    return False


def send_telegram(image_path: str, caption: str) -> bool:
    """Report to Telegram."""
    import urllib.request
    import urllib.parse

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
    boundary = "----FormBoundary" + str(random.randint(100000, 999999))

    with open(image_path, "rb") as f:
        img_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{TG_CHAT_ID}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="meme.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + img_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return data.get("ok", False)
    except Exception as e:
        print(f"  Telegram error: {e}")
        return False


def main():
    # Decide 1 or 2 memes (weighted: 60% one, 40% two)
    num_memes = 1 if random.random() < 0.6 else 2
    print(f"[{time.strftime('%H:%M:%S')}] Generating {num_memes} Kast meme(s)...")

    used_topics = []
    used_styles = []

    for i in range(num_memes):
        # Pick unique topic/style
        topic = random.choice([t for t in TOPICS if t not in used_topics])
        style = random.choice([s for s in STYLES if s not in used_styles])
        used_topics.append(topic)
        used_styles.append(style)

        ts = time.strftime("%Y%m%d_%H%M%S")
        meme_path = str(MEDIA_DIR / f"kast_{ts}_{i}.png")

        print(f"\n[Meme {i+1}/{num_memes}]")
        print(f"  Topic: {topic[:60]}...")
        print(f"  Style: {style[:50]}...")

        # Generate with retry
        success = False
        for attempt in range(1, 4):
            print(f"  Generating (attempt {attempt}/3)...")
            if generate_meme(meme_path, topic, style):
                print(f"  Generated: {meme_path}")
                success = True
                break
            print(f"  Failed, retrying in 15s...")
            time.sleep(15)

        if not success:
            msg = f"❌ Kast meme {i+1} generation FAILED after 3 attempts\nTopic: {topic[:80]}"
            send_telegram_text(msg)
            continue

        # Generate caption
        caption = generate_caption(topic)
        print(f"  Caption: {caption}")

        # Random delay between memes (2-8 min) to look human
        if i > 0:
            delay = random.randint(120, 480)
            print(f"  Waiting {delay}s before posting...")
            time.sleep(delay)

        # Post to Discord with retry
        posted = False
        for attempt in range(1, 4):
            print(f"  Posting to Discord (attempt {attempt}/3)...")
            if post_to_discord(meme_path, caption):
                posted = True
                break
            print(f"  Post failed, retrying in 10s...")
            time.sleep(10)

        # Report to Telegram
        status = "✅ Posted" if posted else "❌ Post FAILED"
        tg_caption = f"📮 Kast meme {i+1}/{num_memes} | {status}\n{caption}"
        tg_ok = send_telegram(meme_path, tg_caption)
        print(f"  Telegram report: {'OK' if tg_ok else 'FAIL'}")

    print(f"\n[{time.strftime('%H:%M:%S')}] All done!")


def send_telegram_text(text):
    """Send text-only message to Telegram."""
    import urllib.request
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": TG_CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    main()

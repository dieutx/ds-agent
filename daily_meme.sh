#!/usr/bin/env bash
# Daily Nous Research meme poster
# 1. Uses hermes (ChatGPT) to generate a meme image
# 2. Uses hermes to generate a caption
# 3. Posts both to Nous Research Discord meme channel + Telegram group
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load secrets from .env
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
fi

DISCORD_TOKEN="${DISCORD_TOKEN:?Set DISCORD_TOKEN in .env}"
CHANNEL_ID="${CHANNEL_ID:-1365353718924709958}"
PROXY="${PROXY:?Set PROXY in .env}"
HERMES="/root/.local/bin/hermes"
TG_BOT_TOKEN="${TG_BOT_TOKEN:?Set TG_BOT_TOKEN in .env}"
TG_CHAT_ID="${TG_CHAT_ID:?Set TG_CHAT_ID in .env}"
MEDIA_DIR="$SCRIPT_DIR/media"

mkdir -p "$MEDIA_DIR"

# Random delay 0-180 min so posting time varies daily
JITTER=$((RANDOM % 10800))
echo "[$(date)] Sleeping ${JITTER}s (~$((JITTER/60))min) for human-like timing..."
sleep "$JITTER"

MEME_FILE="$MEDIA_DIR/meme_$(date +%Y%m%d).png"

echo "[$(date)] Generating meme image with hermes..."

# Nous Research & Hermes specific meme topics
TOPICS=(
  "Hermes model being the most uncensored open-source model and people loving it"
  "Nous Research dropping a new Hermes model and the community going crazy"
  "using Hermes to jailbreak every prompt while GPT refuses everything"
  "teknium staying up at 4am fine-tuning Hermes on weird datasets"
  "Hermes 3 beating closed models on benchmarks and nobody expected it"
  "the Nous Research Discord at 3am debating function calling vs tool use"
  "people switching from ChatGPT to Hermes and never looking back"
  "Hermes model fitting on a single GPU while competitors need a datacenter"
  "Nous Research community submitting PRs and finding bugs at ungodly hours"
  "running Hermes locally and feeling like a hacker while OpenAI charges $20/mo"
  "the Nous Research team casually dropping SOTA models on a random Tuesday"
  "Hermes understanding your weird prompts better than any closed model"
  "Nous Research making open-source AI cool again while big labs gatekeep"
  "people discovering Hermes function calling and losing their minds"
  "the vibe in Nous Discord when a new model drops vs when the server goes down"
)

TOPIC="${TOPICS[$((RANDOM % ${#TOPICS[@]}))]}"

# Rotate meme templates so we don't always get Drake
TEMPLATES=(
  "Drake Hotline Bling (top panel: reject, bottom panel: approve)"
  "Distracted Boyfriend (boyfriend looking at new girl, girlfriend is jealous)"
  "Sleeping Shaq / I Sleep vs Real Shit (boring thing: i sleep, exciting thing: real shit)"
  "Expanding Brain (4 panels from small brain to galaxy brain, increasingly absurd)"
  "Two Buttons (sweating guy choosing between two buttons)"
  "This is Fine (dog sitting in burning room)"
  "Grus Plan (4 panels: plan step 1, step 2, unexpected result, stare at unexpected result)"
  "Batman Slapping Robin (Robin says something wrong, Batman slaps and corrects)"
  "Woman Yelling at Cat (angry woman on left, confused cat at dinner table on right)"
  "Change My Mind (guy at table with sign that has a hot take)"
  "One Does Not Simply (Boromir saying one does not simply do X)"
  "Waiting Skeleton (skeleton on bench waiting for something that takes forever)"
)

TEMPLATE="${TEMPLATES[$((RANDOM % ${#TEMPLATES[@]}))]}"

HOME=/home/hermes_chatgpt "$HERMES" chat -q "Create a meme image about: $TOPIC.

TEMPLATE: Use the '$TEMPLATE' meme format. It must be visually recognizable as this specific meme.

STYLE RULES (follow strictly):
- TEXT MUST BE SHORT: max 5-8 words per text area. Never more.
- The humor comes from the TEMPLATE + SHORT TEXT combo, not walls of text
- Bold Impact font, white text with black outline
- Clean and readable — no clutter, no paragraphs
- Nous Research and Hermes references are encouraged

BAD: 'When you spend 3 hours trying to fine-tune hyperparameters and the loss curve keeps going up'
GOOD: 'GPT: I cant do that' / 'Hermes: say less'

Save to $MEME_FILE." -Q 2>&1 | tail -5

if [ ! -f "$MEME_FILE" ]; then
  echo "[$(date)] ERROR: Meme image not generated at $MEME_FILE"
  exit 1
fi

echo "[$(date)] Meme generated: $MEME_FILE ($(du -h "$MEME_FILE" | cut -f1))"

# Generate caption text — filter out hermes noise (copilot warnings, session ids, box chars)
RAW_CAPTION=$(HOME=/home/hermes_chatgpt "$HERMES" chat -q "Write a very short casual Discord message (max 10 words) to post with a meme about: $TOPIC. Sound like a Nous Research community degen — lazy typing, lowercase, maybe 1 emoji. Can mention Hermes or Nous. No hashtags. Just the message, nothing else." -Q 2>&1)
CAPTION=$(echo "$RAW_CAPTION" | grep -v "session_id:" | grep -v "^$" | grep -v "Copilot" | grep -v "copilot" | grep -v "Hermes" | grep -v "hermes" | grep -v "PAT" | grep -v "ghp_" | grep -v "gho_" | grep -v "OAuth" | grep -v "device code" | grep -v "fine-grained" | grep -v "^╭" | grep -v "^╰" | grep -v "token" | grep -v "validation failed" | sed 's/^[[:space:]]*//' | tail -2)

# Fallback caption if filtering ate everything
if [ -z "$CAPTION" ]; then
  CAPTION="the memes write themselves at this point"
fi

echo "[$(date)] Caption: $CAPTION"

# Post to Discord (try proxy, fallback to direct)
echo "[$(date)] Posting to Discord channel $CHANNEL_ID..."
if ! python3 "$SCRIPT_DIR/post_meme.py" \
  --token "$DISCORD_TOKEN" \
  --channel "$CHANNEL_ID" \
  --proxy "$PROXY" \
  --image "$MEME_FILE" \
  --caption "$CAPTION" 2>/dev/null; then
  echo "[$(date)] Proxy failed, posting direct..."
  python3 "$SCRIPT_DIR/post_meme.py" \
    --token "$DISCORD_TOKEN" \
    --channel "$CHANNEL_ID" \
    --image "$MEME_FILE" \
    --caption "$CAPTION"
fi

# Post to Telegram
echo "[$(date)] Posting to Telegram group $TG_CHAT_ID..."
curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${TG_CHAT_ID}" \
  -F "photo=@${MEME_FILE}" \
  -F "caption=${CAPTION}" | python3 -c "import json,sys; d=json.load(sys.stdin); print('Telegram: OK' if d.get('ok') else f'Telegram: FAIL — {d}')"

echo "[$(date)] Done!"

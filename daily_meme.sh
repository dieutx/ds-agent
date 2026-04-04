#!/usr/bin/env bash
# Daily Nous Research meme poster
# Generates meme with Hermes, posts to Discord + Telegram
# Retries on failure, alerts Telegram on error
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
fi

DISCORD_TOKEN="${DISCORD_TOKEN:?Set DISCORD_TOKEN in .env}"
CHANNEL_ID="${CHANNEL_ID:-1365353718924709958}"
PROXY="${PROXY:-}"
HERMES="/root/.local/bin/hermes"
TG_BOT_TOKEN="${TG_BOT_TOKEN:?Set TG_BOT_TOKEN in .env}"
TG_CHAT_ID="${TG_CHAT_ID:?Set TG_CHAT_ID in .env}"
MEDIA_DIR="$SCRIPT_DIR/media"

mkdir -p "$MEDIA_DIR"

# --- Helper: send Telegram text alert ---
tg_alert() {
  curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":\"${TG_CHAT_ID}\",\"text\":\"$1\"}" > /dev/null 2>&1 || true
}

# --- Trap errors → alert Telegram ---
trap 'tg_alert "❌ Nous meme bot FAILED at line $LINENO\nError: $(tail -3 $SCRIPT_DIR/meme.log 2>/dev/null | head -2)"' ERR

# Random delay 0-180 min
JITTER=$((RANDOM % 10800))
echo "[$(date)] Sleeping ${JITTER}s (~$((JITTER/60))min)..."
sleep "$JITTER"

MEME_FILE="$MEDIA_DIR/meme_$(date +%Y%m%d).png"

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
  "running Hermes locally and feeling like a hacker while OpenAI charges 20 bucks a month"
  "the Nous Research team casually dropping SOTA models on a random Tuesday"
  "Hermes understanding your weird prompts better than any closed model"
  "Nous Research making open-source AI cool again while big labs gatekeep"
  "people discovering Hermes function calling and losing their minds"
  "the vibe in Nous Discord when a new model drops vs when the server goes down"
)

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
  "Stonks (man in suit with rising arrow, feels like a win)"
  "Surprised Pikachu (pikachu shocked face, obvious outcome happens)"
  "Spiderman Pointing at Spiderman (two identical spidermen pointing at each other)"
  "Is This a Pigeon (anime guy pointing at butterfly asking is this X)"
  "Left Exit 12 Off Ramp (car swerving off highway at last second)"
  "Bernie Sanders Asking For Financial Support (I am once again asking for X)"
  "Panik Kalm Panik (3 panels: panic, calm, panic again)"
  "Trade Offer (guy presenting: I receive X, you receive Y)"
  "They are the same picture (Pam from The Office saying both images are the same)"
  "Gigachad (ultra masculine chad face, superiority flex)"
  "NPC meme (gray emotionless NPC face vs enlightened alternative)"
  "Always Has Been (two astronauts in space: wait its all X? always has been)"
)

TOPIC="${TOPICS[$((RANDOM % ${#TOPICS[@]}))]}"
TEMPLATE="${TEMPLATES[$((RANDOM % ${#TEMPLATES[@]}))]}"

echo "[$(date)] Topic: $TOPIC"
echo "[$(date)] Template: $TEMPLATE"

# --- Generate meme with retry ---
GENERATED=false
for attempt in 1 2 3; do
  echo "[$(date)] Generating meme (attempt $attempt/3)..."
  timeout 300 bash -c "HOME=/home/hermes_chatgpt \"$HERMES\" chat -q \"Create a meme image about: $TOPIC.

TEMPLATE: Use the '$TEMPLATE' meme format. It must be visually recognizable as this specific meme.

STYLE RULES (follow strictly):
- TEXT MUST BE SHORT: max 5-8 words per text area. Never more.
- The humor comes from the TEMPLATE + SHORT TEXT combo, not walls of text
- Bold Impact font, white text with black outline
- Clean and readable — no clutter, no paragraphs
- Nous Research and Hermes references are encouraged

BAD: 'When you spend 3 hours trying to fine-tune hyperparameters and the loss curve keeps going up'
GOOD: 'GPT: I cant do that' / 'Hermes: say less'

Save to $MEME_FILE.\" -Q" 2>&1 | tail -5 || true

  if [ -f "$MEME_FILE" ] && [ "$(stat -c%s "$MEME_FILE" 2>/dev/null || echo 0)" -gt 1000 ]; then
    GENERATED=true
    echo "[$(date)] Meme generated: $(du -h "$MEME_FILE" | cut -f1)"
    break
  fi
  echo "[$(date)] Generation failed, retrying in 30s..."
  sleep 30
done

if [ "$GENERATED" != "true" ]; then
  tg_alert "❌ Nous meme: image generation FAILED after 3 attempts\nTopic: ${TOPIC:0:80}"
  exit 1
fi

# --- Generate caption ---
RAW_CAPTION=$(timeout 120 bash -c "HOME=/home/hermes_chatgpt \"$HERMES\" chat -q \"Write a very short casual Discord message (max 10 words) to post with a meme about: $TOPIC. Sound like a Nous Research community degen — lazy typing, lowercase, maybe 1 emoji. Can mention Hermes or Nous. No hashtags. Just the message, nothing else.\" -Q" 2>&1 || echo "")
CAPTION=$(echo "$RAW_CAPTION" | grep -v "session_id:" | grep -v "^$" | grep -v "Copilot" | grep -v "copilot" | grep -v "PAT" | grep -v "ghp_" | grep -v "gho_" | grep -v "OAuth" | grep -v "device code" | grep -v "fine-grained" | grep -v "^╭" | grep -v "^╰" | grep -v "token" | grep -v "validation failed" | sed 's/^[[:space:]]*//' | tail -2)
[ -z "$CAPTION" ] && CAPTION="the memes write themselves at this point"
echo "[$(date)] Caption: $CAPTION"

# --- Post to Discord with retry + proxy fallback ---
DISCORD_OK=false
for attempt in 1 2 3; do
  echo "[$(date)] Posting to Discord (attempt $attempt/3)..."
  if [ -n "$PROXY" ] && python3 "$SCRIPT_DIR/post_meme.py" --token "$DISCORD_TOKEN" --channel "$CHANNEL_ID" --proxy "$PROXY" --image "$MEME_FILE" --caption "$CAPTION" 2>/dev/null; then
    DISCORD_OK=true; break
  fi
  if python3 "$SCRIPT_DIR/post_meme.py" --token "$DISCORD_TOKEN" --channel "$CHANNEL_ID" --image "$MEME_FILE" --caption "$CAPTION" 2>/dev/null; then
    DISCORD_OK=true; break
  fi
  echo "[$(date)] Post failed, retrying in 15s..."
  sleep 15
done

if [ "$DISCORD_OK" != "true" ]; then
  tg_alert "⚠️ Nous meme: Discord post FAILED after 3 attempts (meme generated OK, sending to TG only)"
fi

# --- Post to Telegram ---
curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${TG_CHAT_ID}" \
  -F "photo=@${MEME_FILE}" \
  -F "caption=${CAPTION}" | python3 -c "import json,sys; d=json.load(sys.stdin); print('Telegram: OK' if d.get('ok') else f'Telegram: FAIL — {d}')"

echo "[$(date)] Done! Discord=$DISCORD_OK"

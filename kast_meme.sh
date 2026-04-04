#!/usr/bin/env bash
# Kast meme poster — generates and posts to Kast Discord meme channel
# Retries on failure, alerts Telegram on error
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
fi

KAST_CHANNEL_ID="${KAST_CHANNEL_ID:-1313523536400486400}"
DISCORD_TOKEN="${DISCORD_TOKEN:?Set DISCORD_TOKEN in .env}"
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
trap 'tg_alert "❌ Kast meme bot FAILED at line $LINENO\nError: $(tail -3 $SCRIPT_DIR/kast_meme.log 2>/dev/null | head -2)"' ERR

# Random jitter 0-120 min
JITTER=$((RANDOM % 7200))
echo "[$(date)] Kast meme: Sleeping ${JITTER}s (~$((JITTER/60))min)..."
sleep "$JITTER"

MEME_FILE="$MEDIA_DIR/kast_meme_$(date +%Y%m%d).png"

TOPICS=(
  "me flexing my Kast card at the store while everyone else fumbles with bank apps"
  "traditional bank: please wait 2-5 business days vs Kast: money sent, done"
  "me when I get my Kast card in the mail — tap to pay like a boss"
  "normal people phone: 10 different finance apps vs Kast: everything in one place"
  "the Kast Pengu mascot conquering the world of payments"
  "bank tellers when they see you paying with a Kast crypto card"
  "waiting for my bank transfer vs sending money with Kast instantly"
  "Pengu holding a Kast card like its the infinity gauntlet of finance"
  "friends still using slow bank transfers while I already paid with Kast and left"
  "the whole squad when someone pulls out the black Kast card at dinner"
  "traveling abroad with 5 different cards vs just one Kast card"
  "when the cashier says they accept Visa and you pull out the Kast card"
  "old finance: fees everywhere, slow transfers vs Kast: just works"
  "Kast Pengu watching people still use traditional banks"
  "the vibe when your Kast card arrives vs waiting for bank approval"
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
- Kast card and Pengu (blue penguin mascot) references are encouraged
- NEVER mention AI, bots, Claude, Hermes, or automation

BAD: 'When you spend 20 minutes trying to transfer money and the bank says please wait 2-5 business days'
GOOD: 'Bank: 2-5 business days' / 'Kast: done'

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
  tg_alert "❌ Kast meme: image generation FAILED after 3 attempts\nTopic: ${TOPIC:0:80}"
  exit 1
fi

# --- Generate caption ---
RAW_CAPTION=$(timeout 120 bash -c "HOME=/home/hermes_chatgpt \"$HERMES\" chat -q \"Write a very short casual Discord message (max 8 words) to post with a Kast meme about: $TOPIC. Sound like a real Kast community member — casual, hype about the product, maybe mention the card or Pengu. No hashtags. No AI mention. Just the message, nothing else.\" -Q" 2>&1 || echo "")
CAPTION=$(echo "$RAW_CAPTION" | grep -v "session_id:" | grep -v "^$" | grep -v "Copilot" | grep -v "copilot" | grep -v "PAT" | grep -v "ghp_" | grep -v "gho_" | grep -v "OAuth" | grep -v "device code" | grep -v "fine-grained" | grep -v "^╭" | grep -v "^╰" | grep -v "token" | grep -v "validation failed" | sed 's/^[[:space:]]*//' | tail -2)
[ -z "$CAPTION" ] && CAPTION="kast card hits different fr 🐧"
echo "[$(date)] Caption: $CAPTION"

# --- Post to Discord with retry + proxy fallback ---
DISCORD_OK=false
for attempt in 1 2 3; do
  echo "[$(date)] Posting to Discord (attempt $attempt/3)..."
  if [ -n "$PROXY" ] && python3 "$SCRIPT_DIR/post_meme.py" --token "$DISCORD_TOKEN" --channel "$KAST_CHANNEL_ID" --proxy "$PROXY" --image "$MEME_FILE" --caption "$CAPTION" 2>/dev/null; then
    DISCORD_OK=true; break
  fi
  if python3 "$SCRIPT_DIR/post_meme.py" --token "$DISCORD_TOKEN" --channel "$KAST_CHANNEL_ID" --image "$MEME_FILE" --caption "$CAPTION" 2>/dev/null; then
    DISCORD_OK=true; break
  fi
  echo "[$(date)] Post failed, retrying in 15s..."
  sleep 15
done

if [ "$DISCORD_OK" != "true" ]; then
  tg_alert "⚠️ Kast meme: Discord post FAILED after 3 attempts (meme generated OK, sending to TG only)"
fi

# --- Report to Telegram ---
curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${TG_CHAT_ID}" \
  -F "photo=@${MEME_FILE}" \
  -F "caption=📮 Kast meme posted | ${CAPTION}" | python3 -c "import json,sys; d=json.load(sys.stdin); print('Telegram: OK' if d.get('ok') else f'Telegram: FAIL — {d}')"

echo "[$(date)] Kast meme done! Discord=$DISCORD_OK"

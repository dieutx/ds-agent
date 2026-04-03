#!/usr/bin/env bash
# Kast meme poster — posts 1 meme/day to Kast Discord meme channel
# Style: Kast card, Pengu mascot, comparison panels, product humor
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load secrets from .env
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
fi

KAST_CHANNEL_ID="${KAST_CHANNEL_ID:-1313523536400486400}"
DISCORD_TOKEN="${DISCORD_TOKEN:?Set DISCORD_TOKEN in .env}"
PROXY="${PROXY:?Set PROXY in .env}"
HERMES="/root/.local/bin/hermes"
TG_BOT_TOKEN="${TG_BOT_TOKEN:?Set TG_BOT_TOKEN in .env}"
TG_CHAT_ID="${TG_CHAT_ID:?Set TG_CHAT_ID in .env}"
MEDIA_DIR="$SCRIPT_DIR/media"

mkdir -p "$MEDIA_DIR"

# Random jitter 0-120 min for human-like timing
JITTER=$((RANDOM % 7200))
echo "[$(date)] Kast meme: Sleeping ${JITTER}s (~$((JITTER/60))min) for timing..."
sleep "$JITTER"

MEME_FILE="$MEDIA_DIR/kast_meme_$(date +%Y%m%d).png"

echo "[$(date)] Generating Kast meme..."

# Kast-specific topics — based on actual channel vibe
TOPICS=(
  "me flexing my Kast card at the store while everyone else fumbles with bank apps"
  "traditional bank: please wait 2-5 business days vs Kast: money sent, done"
  "me when I get my Kast card in the mail — tap to pay like a boss, stonks energy"
  "normal people phone: 10 different finance apps vs Kast: everything in one place"
  "the Kast Pengu mascot conquering the world of payments one country at a time"
  "bank tellers when they see you paying with a Kast crypto card at the grocery store"
  "waiting for my bank transfer vs sending money with Kast instantly"
  "me explaining to my grandma that my Kast card works everywhere Visa is accepted"
  "Pengu holding a Kast card like its the infinity gauntlet of finance"
  "friends still using slow bank transfers while I already paid with Kast and left"
  "the whole squad when someone pulls out the black Kast card at dinner"
  "traveling abroad with 5 different cards vs just one Kast card that works globally"
  "me checking my Kast app at 3am because the UI is just too clean"
  "when the cashier says they accept Visa and you pull out the Kast card with lightning design"
  "old finance: fees everywhere, slow transfers, hold music vs Kast: just works"
)

# Kast meme styles — matching what actually gets posted in the channel
STYLES=(
  "Multi-panel comparison meme (2-4 panels): left side shows frustrating old way, right side shows Kast solving it. Include the Kast logo (white K on black) or a dark premium-looking Kast Visa card with lightning design. Clean modern look."
  "Reaction meme with a cute blue penguin mascot (Pengu — Kast's mascot). The penguin is small, round, blue and white with a happy face. Show Pengu doing something confident or funny related to payments/finance. Polished illustration style."
  "Product showcase meme: a sleek dark Kast Visa card (black card, white K logo, lightning bolt design, Mastercard or Visa logo) shown in a cool context — someone flexing it, tapping to pay, or holding it dramatically. Cinematic/premium feel with dark blue/purple lighting."
  "Before/After or expectation vs reality meme about payments. Left panel: old frustrating way (slow bank, fees, multiple apps). Right panel: clean Kast solution. Include the Kast card or Kast logo. Modern clean design, not messy."
  "Classic meme template (Drake, Distracted Boyfriend, Expanding Brain, Stonks guy) but themed around Kast card, Pengu mascot, or Kast payments. Short punchy text, max 5-8 words per section."
)

TOPIC="${TOPICS[$((RANDOM % ${#TOPICS[@]}))]}"
STYLE="${STYLES[$((RANDOM % ${#STYLES[@]}))]}"

echo "[$(date)] Topic: $TOPIC"
echo "[$(date)] Style: ${STYLE:0:60}..."

HOME=/home/hermes_chatgpt "$HERMES" chat -q "Create a meme image for the Kast (kast.xyz) Discord community.

TOPIC: $TOPIC

STYLE: $STYLE

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

Save to $MEME_FILE." -Q 2>&1 | tail -5

if [ ! -f "$MEME_FILE" ]; then
  echo "[$(date)] ERROR: Meme not generated at $MEME_FILE"
  exit 1
fi

echo "[$(date)] Meme generated: $MEME_FILE ($(du -h "$MEME_FILE" | cut -f1))"

# Generate caption
RAW_CAPTION=$(HOME=/home/hermes_chatgpt "$HERMES" chat -q "Write a very short casual Discord message (max 8 words) to post with a Kast meme about: $TOPIC. Sound like a real Kast community member — casual, hype about the product, maybe mention the card or Pengu. No hashtags. No AI mention. Just the message, nothing else." -Q 2>&1)
CAPTION=$(echo "$RAW_CAPTION" | grep -v "session_id:" | grep -v "^$" | grep -v "Copilot" | grep -v "copilot" | grep -v "PAT" | grep -v "ghp_" | grep -v "gho_" | grep -v "OAuth" | grep -v "device code" | grep -v "fine-grained" | grep -v "^╭" | grep -v "^╰" | grep -v "token" | grep -v "validation failed" | sed 's/^[[:space:]]*//' | tail -2)

if [ -z "$CAPTION" ]; then
  CAPTION="kast card hits different fr 🐧"
fi

echo "[$(date)] Caption: $CAPTION"

# Post to Kast Discord channel
echo "[$(date)] Posting to Kast Discord channel $KAST_CHANNEL_ID..."
python3 "$SCRIPT_DIR/post_meme.py" \
  --token "$DISCORD_TOKEN" \
  --channel "$KAST_CHANNEL_ID" \
  --proxy "$PROXY" \
  --image "$MEME_FILE" \
  --caption "$CAPTION"

# Report to Telegram
echo "[$(date)] Reporting to Telegram..."
curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${TG_CHAT_ID}" \
  -F "photo=@${MEME_FILE}" \
  -F "caption=📮 Kast meme posted | ${CAPTION}" | python3 -c "import json,sys; d=json.load(sys.stdin); print('Telegram: OK' if d.get('ok') else f'Telegram: FAIL — {d}')"

echo "[$(date)] Kast meme done!"

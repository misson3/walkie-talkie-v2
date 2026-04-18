# Telegram Walkie-Talkie for Raspberry Pi Zero 2 W

Python service that turns two Raspberry Pi devices into a Telegram-based walkie-talkie.

## Behavior

- Button A (GPIO 12): press once to start recording, press again to stop and send.
- Recording automatically stops after 30 seconds (configurable).
- A NASA Quindar-style two-tone chirp plays when recording stops.
	- If max duration is reached automatically: a distinctive triple-beep alert sounds instead.
- Button B (GPIO 13): replay the latest received voice file.
- Incoming peer-bot voice message is downloaded to a single fixed file.
- Local outgoing recording is saved to a single fixed file.
- Replay is ignored while recording is in progress.

## Files

- Outgoing voice file: `ogg/to-go-voice.ogg`
- Incoming voice file: `ogg/to-play-voice.ogg`
- Python source package: `source/`

## Environment Variables

Required:

- `TELEGRAM_BOT_TOKEN`: bot token for this device (for example, koe1_bot).
- `TELEGRAM_CHAT_ID`: target Telegram group chat ID.

Optional:

- `TELEGRAM_OWN_BOT_USERNAME` (default: empty — recommended to set to e.g. `koe1_bot` to prevent echo)
- `TELEGRAM_IGNORE_BOT_USERNAMES` (default: empty — recommended in V2, comma-separated usernames to ignore on Telegram playback)
- `NODE_ID` (default: `unnamed-node`)
- `MQTT_ENABLED` (default: `false`)
- `MQTT_BROKER_HOST` (default: empty — on Pi A, prefer `127.0.0.1` if the broker runs on the same Pi; on Pi B, use Pi A's Tailscale IP)
- `MQTT_BROKER_PORT` (default: `1883`)
- `MQTT_TOPIC_PREFIX` (default: `walkie/v2`)
- `MQTT_USERNAME` (default: empty)
- `MQTT_PASSWORD` (default: empty)
- `GPIO_RECORD_ACTIVE_LOW` (default: `true`)
- `GPIO_REPLAY_ACTIVE_LOW` (default: `true`)

## System Dependencies (Raspberry Pi)

- `ffmpeg`
- `python3-rpi.gpio`
- ReSpeaker 2-Mic Pi HAT driver and ALSA setup

Example install:

```bash
sudo apt update
sudo apt install -y ffmpeg python3-rpi.gpio
```

## Python Install

```bash
pip install -e .
```

## Run

```bash
export TELEGRAM_BOT_TOKEN="<your_token>"
export TELEGRAM_CHAT_ID="<your_group_chat_id>"
python -m source.main
```

## Run as systemd Service (auto-start on boot)

A ready-made unit file is included: `walkie-talkie.service`.

### 1. Confirm the venv exists on the Pi

```bash
cd ~/walkie-talkie-v2
uv sync           # creates .venv if not already present
```

### 2. Update the env file to add OWN_BOT_USERNAME

```bash
sudo nano /etc/walkie-talkie/walkie-talkie.env
```

Add (or verify) this line:

```
TELEGRAM_OWN_BOT_USERNAME=koe1_bot
```

You can safely remove the `TELEGRAM_PEER_BOT_USERNAME` line — it is no longer used.

### 3. Install the unit file

```bash
sudo cp ~/walkie-talkie-v2/walkie-talkie.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 4. Enable and start the service

```bash
sudo systemctl enable walkie-talkie    # auto-start on every boot
sudo systemctl start walkie-talkie     # start right now without rebooting
```

### 5. Check it is running

```bash
sudo systemctl status walkie-talkie
```

### 6. Follow live logs

```bash
journalctl -u walkie-talkie -f
```

### Useful service management commands

| Command | Purpose |
|---|---|
| `sudo systemctl stop walkie-talkie` | Stop the service |
| `sudo systemctl restart walkie-talkie` | Restart after a code update |
| `sudo systemctl disable walkie-talkie` | Disable auto-start |

### After a code update on the Pi

```bash
cd ~/walkie-talkie-v2
git pull
uv sync
sudo systemctl restart walkie-talkie
```

---

## Hardware Smoke Test

Use this before full app runs to verify button polarity and LED role mapping.

```bash
export TELEGRAM_BOT_TOKEN="<your_token>"
export TELEGRAM_CHAT_ID="<your_group_chat_id>"
python -m source.hardware_smoke_test --seconds 20
```

Expected result:

- LED1 stays green while test is running.
- Press Button A: LED2 turns red while pressed.
- Press Button B: LED3 turns blue while pressed.

## Audio Smoke Test

After hardware test passes, verify audio recording in OGG format.

```bash
export TELEGRAM_BOT_TOKEN="<your_token>"
export TELEGRAM_CHAT_ID="<your_group_chat_id>"
python -m source.audio_smoke_test --seconds 5
```

Expected result:

- Recording starts and stops cleanly.
- Output file: /tmp/audio_smoke_test.ogg
- File size > 0 bytes.
- `file` command shows OGG/Opus format.
- Optionally playback: `aplay -D hw:1,0 /tmp/audio_smoke_test.ogg`

## PC-Side V2 Verification

Use this on the PC before deploying to Raspberry Pi. It checks V2 config parsing, Telegram bot-ignore rules, and MQTT topic acceptance rules without touching GPIO, LEDs, or audio hardware.

```bash
python -m source.v2_pc_verification
```

Expected result:

- Config values are normalized as expected.
- Human Telegram sender is accepted.
- Bot Telegram senders in the ignore list are rejected.
- MQTT peer topics are accepted.
- MQTT own-node and malformed topics are rejected.

## Notes

- Recording and playback use `ffmpeg` subprocess commands.
- LED patterns use `source/interfaces/pixels.py` and `source/interfaces/apa102.py`.
- Button A (GPIO12) and Button B (GPIO13) default to pull-up wiring (active-low).
- For active-high wiring, set `GPIO_RECORD_ACTIVE_LOW=false` and/or `GPIO_REPLAY_ACTIVE_LOW=false`.
- Telegram polling uses retry with exponential backoff on transient API errors.

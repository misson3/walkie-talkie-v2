# Telegram Walkie-Talkie for Raspberry Pi Zero 2 W

Python service that turns two Raspberry Pi devices into a Telegram-based walkie-talkie.

## Behavior

- Button A (GPIO 12): press once to start recording, press again to stop and send.
- Recording automatically stops after 30 seconds (configurable).
- A NASA Quindar-style two-tone chirp plays when recording stops.
	- If max duration is reached automatically: a distinctive triple-beep alert sounds instead.
- Button B (GPIO 17): replay the latest received voice file.
- Incoming peer-bot voice message is downloaded to a single fixed file.
- Local outgoing recording is saved to a single fixed file.
- Replay is ignored while recording is in progress.

## Files

- Outgoing voice file: `to-go-voice.ogg`
- Incoming voice file: `to-play-voice.ogg`

## Environment Variables

Required:

- `TELEGRAM_BOT_TOKEN`: bot token for this device (for example, koe1_bot).
- `TELEGRAM_CHAT_ID`: target Telegram group chat ID.

Optional:

- `TELEGRAM_OWN_BOT_USERNAME` (default: empty — recommended to set to e.g. `koe1_bot` to prevent echo)
- `AUDIO_DEVICE` (default: `hw:1,0`)
- `GPIO_RECORD_PIN` (default: `12`)
- `GPIO_REPLAY_PIN` (default: `17`)
- `GPIO_RECORD_ACTIVE_LOW` (default: `true`)
- `GPIO_REPLAY_ACTIVE_LOW` (default: `true`)
- `GPIO_DEBOUNCE_MS` (default: `120`)
- `TELEGRAM_POLL_INTERVAL_S` (default: `1.5`)
- `MAX_RECORDING_DURATION_S` (default: `30.0` seconds)
- `SEND_FILE_NAME` (default: `to-go-voice.ogg`)
- `PLAY_FILE_NAME` (default: `to-play-voice.ogg`)

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
python main.py
```

## Run as systemd Service (auto-start on boot)

A ready-made unit file is included: `walkie-talkie.service`.

### 1. Confirm the venv exists on the Pi

```bash
cd ~/z2w2-walkie-talkie-Mar28-2026
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
sudo cp ~/z2w2-walkie-talkie-Mar28-2026/walkie-talkie.service /etc/systemd/system/
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
cd ~/z2w2-walkie-talkie-Mar28-2026
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
python hardware_smoke_test.py --seconds 20
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
python audio_smoke_test.py --seconds 5
```

Expected result:

- Recording starts and stops cleanly.
- Output file: /tmp/audio_smoke_test.ogg
- File size > 0 bytes.
- `file` command shows OGG/Opus format.
- Optionally playback: `aplay -D hw:1,0 /tmp/audio_smoke_test.ogg`

## Notes

- Recording and playback use `ffmpeg` subprocess commands.
- LED patterns use `interfaces/pixels.py` and `interfaces/apa102.py`.
- Button A (GPIO12) and Button B (GPIO17) default to pull-up wiring (active-low).
- For active-high wiring, set `GPIO_RECORD_ACTIVE_LOW=false` and/or `GPIO_REPLAY_ACTIVE_LOW=false`.
- Telegram polling uses retry with exponential backoff on transient API errors.

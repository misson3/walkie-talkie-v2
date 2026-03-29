# Telegram Walkie-Talkie for Raspberry Pi Zero 2 W

Python service that turns two Raspberry Pi devices into a Telegram-based walkie-talkie.

## Behavior

- Button A (GPIO 12): press once to start recording, press again to stop and send.
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

- `TELEGRAM_PEER_BOT_USERNAME` (default: `koe2_bot`)
- `AUDIO_DEVICE` (default: `hw:1,0`)
- `GPIO_RECORD_PIN` (default: `12`)
- `GPIO_REPLAY_PIN` (default: `17`)
- `GPIO_RECORD_ACTIVE_LOW` (default: `true`)
- `GPIO_REPLAY_ACTIVE_LOW` (default: `true`)
- `GPIO_DEBOUNCE_MS` (default: `120`)
- `TELEGRAM_POLL_INTERVAL_S` (default: `1.5`)
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

## Notes

- Recording and playback use `ffmpeg` subprocess commands.
- LED patterns use `interfaces/pixels.py` and `interfaces/apa102.py`.
- Button A (GPIO12) and Button B (GPIO17) default to pull-up wiring (active-low).
- For active-high wiring, set `GPIO_RECORD_ACTIVE_LOW=false` and/or `GPIO_REPLAY_ACTIVE_LOW=false`.

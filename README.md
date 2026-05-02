# Telegram Walkie-Talkie for Raspberry Pi Zero 2 W

Python service that turns two Raspberry Pi devices into a Telegram-based walkie-talkie.

## Reproducible Setup (Git Clone -> Two Raspberry Pis)

This project is intended to run as a two-node setup:

- Pi A: runs the app and Mosquitto broker.
- Pi B: runs the app and connects to Pi A's broker over Tailscale.

For full detailed deployment notes, see `DEPLOY_NEW_PI.md`.

### 1. On both Pi nodes, install base packages and uv

```bash
sudo apt update
sudo apt install -y ffmpeg python3-rpi.gpio python3-dev git curl
curl -LsSf https://astral.sh/uv/install.sh | sh
reboot
```

After reboot:

```bash
which uv
uv --version
```

### 2. Clone this repository

```bash
cd /home/pison
git clone <YOUR_REPO_URL> walkie-talkie-v2
cd walkie-talkie-v2
```

### 3. Create project venv from lock file

```bash
uv python install
uv sync --frozen
```

If `--frozen` fails due to local Python differences, run:

```bash
uv sync
```

#### if following error occurs with the `uv sync`

```bash
error: command '/usr/bin/cc' failed with exit code 1

      hint: This error likely indicates that you need to install a library that provides
      "ffi.h" for `cffi@2.0.0`
  help: `cffi` (v2.0.0) was included because `tg-w-t-mar29-2026` (v0.1.0) depends on
        `google-cloud-speech` (v2.38.0) which depends on `google-auth` (v2.50.0) which depends
        on `cryptography` (v47.0.0) which depends on `cffi`
```

Try followings

```bash
sudo apt update
sudo apt install -y libffi-dev libssl-dev python3-dev build-essential pkg-config

# then,
uv sync
```



### 4. Create per-node env file

```bash
sudo install -d -m 700 /etc/walkie-talkie
sudo cp /home/pison/walkie-talkie-v2/walkie-talkie.env.template /etc/walkie-talkie/walkie-talkie.env
sudo nano /etc/walkie-talkie/walkie-talkie.env
sudo chmod 600 /etc/walkie-talkie/walkie-talkie.env
sudo chown root:root /etc/walkie-talkie/walkie-talkie.env
```

Set node-specific values:

- Pi A: `NODE_ID=pi_a`, `MQTT_ENABLED=true`, `MQTT_BROKER_HOST=127.0.0.1`
- Pi B: `NODE_ID=pi_b`, `MQTT_ENABLED=true`, `MQTT_BROKER_HOST=<PI_A_TAILSCALE_IP>`
- Both: set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_OWN_BOT_USERNAME`, and `TELEGRAM_IGNORE_BOT_USERNAMES`

### 5. Set up Tailscale on both nodes

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

### 6. On Pi A, set up Mosquitto broker

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo tee /etc/mosquitto/conf.d/walkie-v2.conf > /dev/null <<'EOF'
per_listener_settings true
listener 1883 127.0.0.1
allow_anonymous true

listener 1883 <PI_A_TAILSCALE_IP>
allow_anonymous true
EOF
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto
sudo systemctl status mosquitto
```

### 7. Install and start app service on both nodes

```bash
sudo cp /home/pison/walkie-talkie-v2/walkie-talkie.service /etc/systemd/system/walkie-talkie.service
sudo systemctl daemon-reload
sudo systemctl enable walkie-talkie
sudo systemctl restart walkie-talkie
sudo systemctl status walkie-talkie
journalctl -u walkie-talkie -f
```

### 8. Verify end-to-end

- Record on Pi A and confirm playback on Pi B.
- Record on Pi B and confirm playback on Pi A.
- Confirm bot-originated Telegram voice is ignored for playback.

## Behavior

- Button A (GPIO 12): press once to start recording, press again to stop and send.
- Recording automatically stops after 30 seconds (configurable).
  - If max duration is reached: a distinctive beep alert is given.
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

- `TELEGRAM_BOT_TOKEN`: bot token for this device.
- `TELEGRAM_CHAT_ID`: target Telegram group chat ID.

Optional:

- `TELEGRAM_OWN_BOT_USERNAME` (default: empty — recommended to set to e.g. `koe1_bot` to prevent echo)
- `TELEGRAM_IGNORE_BOT_USERNAMES` (default: empty — recommended in V2, comma-separated usernames to ignore on Telegram playback)
- `NODE_ID` (default: `unnamed-node`)
- `MQTT_ENABLED` (default: `false`)
- `MQTT_BROKER_HOST` (default: empty — validated setup: on Pi A use `127.0.0.1`, on Pi B use Pi A's Tailscale IP, and configure Mosquitto on Pi A to listen on both)
- `MQTT_BROKER_PORT` (default: `1883`)
- `MQTT_TOPIC_PREFIX` (default: `walkie/v2`)
- `MQTT_USERNAME` (default: empty)
- `MQTT_PASSWORD` (default: empty)
- `AUDIO_DEVICE` (default: `hw:1,0`)
- `GPIO_RECORD_PIN` (default: `12`)
- `GPIO_REPLAY_PIN` (default: `13`)
- `GPIO_RECORD_ACTIVE_LOW` (default: `true`)
- `GPIO_REPLAY_ACTIVE_LOW` (default: `true`)
- `DEBOUNCE_MS` (default: `120`)
- `POLL_INTERVAL_S` (default: `1.5`)
- `MAX_RECORDING_DURATION_S` (default: `30.0`)
- `SEND_FILE_NAME` (default: `to-go-voice.ogg`)
- `PLAY_FILE_NAME` (default: `to-play-voice.ogg`)
- `NOTIFICATION_SOUND_NAME` (default: `doorbell_short_decay.ogg`)
- `RECORDING_START_SOUND_NAME` (default: `rec_start_A.ogg`)
- `RECORDING_STOP_SOUND_NAME` (default: `rec_stop_A.ogg`)
- `PLAYBACK_END_SOUND_NAME` (default: `rec_stop_C.ogg`)
- `MAX_DURATION_ALERT_SOUND_NAME` (default: `max_dur_B.ogg`)

## System Dependencies (Raspberry Pi)

- `ffmpeg`
- `python3-rpi.gpio`
- ReSpeaker 2-Mic Pi HAT driver and ALSA setup (see `installation-memo.md`)

Full provisioning/service setup steps are covered in `DEPLOY_NEW_PI.md`.

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

## Optional: Google Speech-to-Text (Post-MQTT)

This project can optionally run speech-to-text for the local outgoing file `ogg/to-go-voice.ogg`.

- Trigger timing: runs only after a successful MQTT publish of a local recording.
- Existing flow remains unchanged: Telegram send and MQTT publish happen first.
- STT is best-effort: failures are logged and do not interrupt walkie-talkie behavior.
- On STT success, transcript text is posted to the configured Telegram chat.

Important runtime condition:

- STT path executes only when MQTT is enabled and publish succeeds.
- If MQTT is disabled or publish fails, STT is skipped by design.

Required env vars for STT:

- `STT_ENABLED=true`
- `STT_LANGUAGE_CODE=ja-JP` (or your target language)
- `GOOGLE_APPLICATION_CREDENTIALS=/etc/walkie-talkie/gcp-service-account.json`

Optional STT vars:

- `STT_MODEL=` (empty means API default model selection)
- `STT_TIMEOUT_S=15`

Audio format handling:

- Direct recognition uses OGG Opus (`OGG_OPUS`) from `ogg/to-go-voice.ogg`.
- If direct request is rejected with `InvalidArgument`, app converts to FLAC via `ffmpeg` and retries once.

Credentials file note (important on Raspberry Pi):

- `walkie-talkie.service` runs as user `pison`.
- The key file path in `GOOGLE_APPLICATION_CREDENTIALS` must be readable by `pison`.
- If key is stored under `/etc/walkie-talkie`, make directory/file permissions compatible with that user.

## file permissions

- the .env file must be readable by system (root).  Systemd reads EnvironmenFile as root before starting the process.
- the .json file must be readable by the service runtime user.  


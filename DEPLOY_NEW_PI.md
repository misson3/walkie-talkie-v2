# Deploy To A New Raspberry Pi

This guide sets up a fresh Raspberry Pi as another walkie-talkie node.

## 1. Create a new Telegram bot

1. Open Telegram and chat with BotFather.
2. Send `/newbot` and follow prompts.
3. Save the bot token (looks like `123456789:AA...`).
4. Set username (must end with `bot`, example `koe3_bot`).
5. Optional but recommended:
   - `/setname` for a readable display name.
   - `/setdescription` and `/setabouttext`.
6. Disable privacy mode so group voice messages are visible:
   - `/setprivacy`
   - Choose your bot
   - Select `Disable`

## 2. Add the bot to your group

1. Add the new bot account to the target group chat.
2. Make sure the bot is allowed to read/send voice messages.

## 3. Get the group chat id

Use one of these methods:

- Method A (simple): Add @RawDataBot to the group and read `chat.id`.
- Method B (direct):
  1. Send one message in the group.
  2. Run:
     `curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"`
  3. Find `chat.id` (often negative for groups).

## 4. Prepare Raspberry Pi packages and uv

```bash
sudo apt update
sudo apt install -y ffmpeg python3-rpi.gpio python3-dev git curl
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

If your HAT driver steps are needed, complete those first and verify ALSA device exists.

## 5. Copy project and build the venv with uv

Copy the full project so metadata files are included:

- `pyproject.toml`
- `uv.lock`
- `.python-version`

```bash
cd /home/pison
git clone <YOUR_REPO_URL> tg-w-t-Mar29-2026
cd tg-w-t-Mar29-2026

# Install/select Python from project metadata, then create .venv and install deps
uv python install
uv sync
```

If you want strict reproducible install from the lock file:

```bash
uv sync --frozen
```

Note: if `uv sync` reports a Python-version mismatch, align `.python-version` with the `requires-python` value in `pyproject.toml`, then rerun `uv python install` and `uv sync`.

## 6. Create secure env file from template

```bash
sudo install -d -m 700 /etc/walkie-talkie
sudo cp /home/pison/tg-w-t-Mar29-2026/walkie-talkie.env.template /etc/walkie-talkie/walkie-talkie.env
sudo nano /etc/walkie-talkie/walkie-talkie.env
```

Set values:

- `TELEGRAM_BOT_TOKEN` = token from BotFather
- `TELEGRAM_CHAT_ID` = target group chat id
- `TELEGRAM_OWN_BOT_USERNAME` = this bot username without @

Then lock permissions:

```bash
sudo chmod 600 /etc/walkie-talkie/walkie-talkie.env
sudo chown root:root /etc/walkie-talkie/walkie-talkie.env
```

## 7. Install systemd service

Edit service path if needed:

- `WorkingDirectory` in `walkie-talkie.service`
- `ExecStart` in `walkie-talkie.service`

Then install:

```bash
sudo cp /home/pison/tg-w-t-Mar29-2026/walkie-talkie.service /etc/systemd/system/walkie-talkie.service
sudo systemctl daemon-reload
sudo systemctl enable walkie-talkie
sudo systemctl start walkie-talkie
```

## 8. Validate service

```bash
sudo systemctl status walkie-talkie
journalctl -u walkie-talkie -f
```

## 9. Smoke test checklist

1. LED1 green is on when service starts.
2. Press record button once: start beep plays, recording begins.
3. Press record button again: recording stops, end beep plays, upload starts.
4. Send a voice message in group: auto-download and playback works.
5. Playback-end beep is heard.

## 10. Update workflow on Pi

```bash
cd /home/pison/tg-w-t-Mar29-2026
git pull
uv sync --frozen
sudo systemctl restart walkie-talkie
journalctl -u walkie-talkie -n 80 --no-pager
```

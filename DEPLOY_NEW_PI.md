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

🐔# the script add the path setting in ~/.profile
🐔# just reboot to take the setting in effect
#export PATH="$HOME/.local/bin:$PATH"

🐔# after the reboot, check
which uv
uv --version
# uv 0.11.6 (armv7-unknown-linux-gnueabihf) # on my z2w3
```

If your HAT driver steps are needed, complete those first and verify ALSA device exists. 

👉see my installation-memo.md for the Respeaker Mic-2 installation.



## 5. Copy project and build the venv with uv

Copy the full project so metadata files are included:

- `pyproject.toml`
- `uv.lock`
- `.python-version`

```bash
cd /home/pison
git clone <YOUR_REPO_URL> walkie-talkie-v2
cd walkie-talkie-v2

# Install/select Python from project metadata, then create .venv and install deps
uv python install
uv sync
```

If you prefer to copy files manually instead of cloning, create the deployment directory first and place the project files there:

```bash
cd /home/pison
mkdir -p walkie-talkie-v2
cd walkie-talkie-v2
```

If you want strict reproducible install from the lock file:

```bash
uv sync --frozen
```

Note: if `uv sync` reports a Python-version mismatch, align `.python-version` with the `requires-python` value in `pyproject.toml`, then rerun `uv python install` and `uv sync`.

## 6. Create secure env file from template

```bash
sudo install -d -m 700 /etc/walkie-talkie
sudo cp /home/pison/walkie-talkie-v2/walkie-talkie.env.template /etc/walkie-talkie/walkie-talkie.env
sudo nano /etc/walkie-talkie/walkie-talkie.env
```

Set values:

- `TELEGRAM_BOT_TOKEN` = token from BotFather
- `TELEGRAM_CHAT_ID` = target group chat id
- `TELEGRAM_OWN_BOT_USERNAME` = this bot username without @
- `TELEGRAM_IGNORE_BOT_USERNAMES` = both Pi bot usernames, comma-separated
- `NODE_ID` = `pi_a` or `pi_b`
- `MQTT_ENABLED` = `true` for V2
- `MQTT_BROKER_HOST` = on Pi A, prefer `127.0.0.1` when Mosquitto runs on the same Pi; on Pi B, use Pi A's Tailscale IP
- `MQTT_BROKER_PORT` = `1883`
- `MQTT_TOPIC_PREFIX` = `walkie/v2`
- `MQTT_USERNAME` = optional username when Mosquitto auth is enabled
- `MQTT_PASSWORD` = optional password when Mosquitto auth is enabled

Then lock permissions:

```bash
sudo chmod 600 /etc/walkie-talkie/walkie-talkie.env
sudo chown root:root /etc/walkie-talkie/walkie-talkie.env
```

## 7. Set up Tailscale on Pi A and Pi B

Do this on both Raspberry Pi nodes before MQTT setup.

Install Tailscale:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale version
```

Join the tailnet:

```bash
sudo tailscale up
```

The command prints a login URL. Open it in a browser and authenticate with the same Tailscale account on both Pi A and Pi B.

Confirm the node is online and record its Tailscale IPv4 address:

```bash
tailscale status
tailscale ip -4
```

Completion criteria:

1. Both Pi A and Pi B appear in the Tailscale admin machines page.
2. Both Pi A and Pi B return a `100.x.x.x` IPv4 address from `tailscale ip -4`.
3. Pi A can ping Pi B's Tailscale IP.
4. Pi B can ping Pi A's Tailscale IP.

Example ping check from Pi A:

```bash
ping -c 4 <PI_B_TAILSCALE_IP>
```

Example ping check from Pi B:

```bash
ping -c 4 <PI_A_TAILSCALE_IP>
```

If you need to re-authenticate:

```bash
sudo tailscale logout
sudo tailscale up
```

## 8. Set up Mosquitto broker on Pi A

Do this on Pi A only after Tailscale works on both nodes.

Install Mosquitto:

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

Create an initial listener config for bring-up:

```bash
sudo nano /etc/mosquitto/conf.d/walkie-v2.conf
```

Use this initial content:

```conf
per_listener_settings true
listener 1883
allow_anonymous true
```

Restart and verify the broker:

```bash
sudo systemctl restart mosquitto
sudo systemctl status mosquitto
sudo ss -lntp | grep 1883
```

Local publish/subscribe test on Pi A:

Terminal 1:

```bash
mosquitto_sub -h 127.0.0.1 -t walkie/v2/audio/# -v
```

Terminal 2:

```bash
mosquitto_pub -h 127.0.0.1 -t walkie/v2/audio/pi_test -m hello-from-pi-a
```

Remote publish/subscribe test from Pi B using Pi A's Tailscale IP:

```bash
mosquitto_sub -h <PI_A_TAILSCALE_IP> -t walkie/v2/audio/# -v
mosquitto_pub -h <PI_A_TAILSCALE_IP> -t walkie/v2/audio/pi_b -m hello-from-pi-b
```

After initial bring-up, better target config is to bind the listener to Pi A's Tailscale IP instead of all interfaces:

```conf
per_listener_settings true
listener 1883 <PI_A_TAILSCALE_IP>
allow_anonymous true
```

Longer-term hardening after end-to-end validation:

1. Keep the listener bound to the Tailscale IP.
2. Change `allow_anonymous` to `false`.
3. Add a `password_file` and MQTT credentials.

Example authenticated Mosquitto setup on Pi A:

```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd walkie
sudo chmod 600 /etc/mosquitto/passwd
sudo chown root:root /etc/mosquitto/passwd
```

Then update `/etc/mosquitto/conf.d/walkie-v2.conf`:

```conf
per_listener_settings true
listener 1883 <PI_A_TAILSCALE_IP>
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Restart and verify:

```bash
sudo systemctl restart mosquitto
mosquitto_sub -h <PI_A_TAILSCALE_IP> -u walkie -P <MQTT_PASSWORD> -t walkie/v2/audio/# -v
mosquitto_pub -h <PI_A_TAILSCALE_IP> -u walkie -P <MQTT_PASSWORD> -t walkie/v2/audio/pi_b -m hello-auth
```

When using authenticated Mosquitto, set the same `MQTT_USERNAME` and `MQTT_PASSWORD` in `/etc/walkie-talkie/walkie-talkie.env` on both Pi nodes.

## 9. Install systemd service

Edit service path if needed:

- `WorkingDirectory` in `walkie-talkie.service`
- `ExecStart` in `walkie-talkie.service`

Then install:

```bash
sudo cp /home/pison/walkie-talkie-v2/walkie-talkie.service /etc/systemd/system/walkie-talkie.service
sudo systemctl daemon-reload
sudo systemctl enable walkie-talkie
sudo systemctl start walkie-talkie
```

## 10. Validate service

```bash
sudo systemctl status walkie-talkie
journalctl -u walkie-talkie -f
```

## 11. Smoke test checklist

1. LED1 green is on when service starts.
2. Press record button once: start beep plays, recording begins.
3. Press record button again: recording stops, end beep plays, upload starts.
4. Send a voice message in group: auto-download and playback works.
5. Playback-end beep is heard.
6. Pi A local record reaches Pi B over MQTT and plays once.
7. Pi B local record reaches Pi A over MQTT and plays once.
8. Human Telegram voice reaches both Pi nodes and plays once.
9. Bot-originated Telegram voices are ignored for playback.

## 12. Update workflow on Pi

```bash
cd /home/pison/walkie-talkie-v2
git pull
uv sync --frozen
sudo systemctl restart walkie-talkie
journalctl -u walkie-talkie -n 80 --no-pager
```

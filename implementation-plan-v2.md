# Walkie-Talkie V2 Implementation Plan

Based on [design-input-for-v2.md](design-input-for-v2.md).

## 1. Goal

Build a two-node voice messaging system with these paths:

- Human user -> Telegram group -> both Raspberry Pi nodes receive and play once.
- Pi A or Pi B local recording -> Telegram group as activity log.
- Pi A or Pi B local recording -> MQTT over Tailscale -> peer Raspberry Pi receives and plays once.

## 2. Architecture Decisions To Fix First

Before implementation, lock these rules to avoid duplicate playback and message loops.

1. Telegram is the human-facing log and human input path.
2. MQTT is the inter-Pi delivery path for Pi-originated recordings.
3. A voice message recorded on a Pi must not be replayed twice on the peer.
4. Bot-originated Telegram voice messages must be ignored by both Pi apps for playback purposes.
5. Human-originated Telegram voice messages must still be accepted by both Pi apps.

This means the current Telegram polling logic needs one change in V2:

- ignore any Telegram message sent by any configured bot identity, not only by the local bot itself.

## 3. Recommended Delivery Model

Use this event model:

1. Human sends voice to Telegram group.
2. Both Pi nodes download from Telegram and play once.
3. Pi A records local voice.
4. Pi A sends the voice file to Telegram as a log.
5. Pi A publishes the recorded `.ogg` payload and metadata to MQTT.
6. Pi B receives the MQTT message, saves it locally, and plays once.
7. Pi B does not replay the same message from Telegram because bot-originated Telegram messages are ignored.

This is the lowest-complexity model because it avoids needing shared file storage or HTTP file serving between Pi nodes.

## 4. Development Phases

### Phase 0: Spec Lock

1. Confirm topic naming, bot usernames, and broker host.
2. Confirm whether Pi A is always the broker, or whether broker placement should be configurable.
3. Decide MQTT payload format.
4. Decide size limit and retention policy for audio files.

Recommended MQTT payload approach:

- topic: `walkie/v2/audio/<sender_id>`
- payload: binary `.ogg`
- metadata in MQTT v5 user properties or a paired JSON topic

If you want the simplest implementation, use two topics:

- `walkie/v2/audio/<sender_id>/meta`
- `walkie/v2/audio/<sender_id>/data`

But a single binary message with small JSON header encoded separately is better only if you want to invest in protocol design. For V2, simplest practical path is:

- publish raw `.ogg` bytes to a topic
- include sender id and timestamp in topic or filename

### Phase 1: PC-Side Code Refactor And Local Implementation

Work on the PC first, without requiring live Pi hardware for each code change.

1. Extend configuration model.
2. Add MQTT client module.
3. Refactor message routing so Telegram and MQTT are separate input channels.
4. Add sender filtering logic for Telegram.
5. Add file save and playback path for MQTT-received audio.
6. Add logging for source type: `telegram-human`, `telegram-bot-ignored`, `mqtt-peer`.
7. Add simple smoke test hooks or dry-run mode where possible.

Code tasks:

1. Add new config fields in `source/config.py` for MQTT and bot filtering.
2. Add a new module such as `source/mqtt_handler.py`.
3. Refactor `source/main.py` to integrate an MQTT listener task.
4. Update Telegram handling in `source/telegram_handler.py` to support ignore-list filtering.
5. Save MQTT-received audio into the same local playback file path used by the current replay flow.

New environment variables recommended:

- `NODE_ID=pi_a` or `pi_b`
- `MQTT_ENABLED=true`
- `MQTT_BROKER_HOST=100.x.x.x`
- `MQTT_BROKER_PORT=1883`
- `MQTT_TOPIC_PREFIX=walkie/v2`
- `TELEGRAM_IGNORE_BOT_USERNAMES=koe1_bot,koe2_bot`

Recommended Python dependency:

- `paho-mqtt`

### Phase 2: PC-Side Verification

Before touching both Pi nodes, verify the non-hardware logic.

1. Unit-test config parsing.
2. Unit-test Telegram sender filtering rules.
3. Unit-test MQTT topic generation and message acceptance rules.
4. Dry-run message flow with recorded `.ogg` files already in the repo or generated locally.
5. Verify no double-play paths exist in code.

Important acceptance criteria:

1. Human Telegram voice is accepted and played.
2. Local bot Telegram voice is ignored.
3. Peer bot Telegram voice is ignored.
4. MQTT audio from peer is accepted, saved, and played.
5. Replay button still replays the latest downloaded or MQTT-received audio.

### Phase 3: Common Raspberry Pi Setup

Apply on both Pi A and Pi B.

1. Base OS update.
2. Audio HAT and ALSA verification.
3. `uv` and Python environment setup.
4. Project deployment.
5. Service installation.
6. Tailscale installation.

Checklist:

1. `ffmpeg`, `python3-rpi.gpio`, `python3-dev`, `git`, `curl` installed.
2. ReSpeaker card visible via `aplay -l` and `arecord -l`.
3. ALSA settings restored on boot if still required.
4. Project copied to both nodes.
5. `uv sync --frozen` succeeds.

### Phase 4: Tailscale Setup On Both Pi Nodes

Do this on both Pi A and Pi B.

1. Install Tailscale.
2. Join both devices to the same tailnet.
3. Record each node's Tailscale IP.
4. Verify connectivity with `ping` and `tailscale status`.

Suggested commands:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
tailscale status
```

Validation:

1. Pi A can ping Pi B Tailscale IP.
2. Pi B can ping Pi A Tailscale IP.
3. Hostname resolution works, or raw `100.x.x.x` IPs are recorded in the env file.

### Phase 5: MQTT Broker Setup

Start with Pi A as the broker.

1. Install Mosquitto on Pi A.
2. Bind listener for Tailscale-reachable interface.
3. Start with a simple setup, then harden.
4. Verify broker access from Pi B.

Initial simple setup:

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
```

Config file example:

```conf
listener 1883
allow_anonymous true
```

Recommended hardening after first end-to-end test:

1. Restrict broker to Tailscale only.
2. Add username/password.
3. Avoid anonymous access long-term.

Better target configuration after initial prototype:

1. Mosquitto bound to Tailscale IP or all interfaces with firewall/Tailscale restriction.
2. `password_file` enabled.
3. Unique MQTT credentials stored in `/etc/walkie-talkie/walkie-talkie.env`.

### Phase 6: Per-Pi App Configuration

Prepare separate env files on each node.

Pi A example:

```env
NODE_ID=pi_a
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_OWN_BOT_USERNAME=koe1_bot
TELEGRAM_IGNORE_BOT_USERNAMES=koe1_bot,koe2_bot
MQTT_ENABLED=true
MQTT_BROKER_HOST=<pi_a_tailscale_ip>
MQTT_BROKER_PORT=1883
MQTT_TOPIC_PREFIX=walkie/v2
```

Pi B example:

```env
NODE_ID=pi_b
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_OWN_BOT_USERNAME=koe2_bot
TELEGRAM_IGNORE_BOT_USERNAMES=koe1_bot,koe2_bot
MQTT_ENABLED=true
MQTT_BROKER_HOST=<pi_a_tailscale_ip>
MQTT_BROKER_PORT=1883
MQTT_TOPIC_PREFIX=walkie/v2
```

### Phase 7: End-To-End Bring-Up On Same LAN

Do early validation while both devices are physically nearby.

Test order:

1. Pi A local record -> Telegram log confirmed.
2. Pi A local record -> MQTT transfer -> Pi B playback confirmed.
3. Pi B local record -> Telegram log confirmed.
4. Pi B local record -> MQTT transfer -> Pi A playback confirmed.
5. Human Telegram voice -> both Pi nodes playback confirmed.
6. Confirm bot-originated Telegram voices are ignored for playback.
7. Confirm replay button still works on each Pi.

### Phase 8: Remote-Network Validation

After same-LAN success:

1. Move Pi A and Pi B onto separate LANs.
2. Verify Tailscale still connects both nodes.
3. Verify MQTT transfer still works.
4. Verify Telegram behavior is unchanged.
5. Measure latency and retry behavior.

## 5. Practical Build Order

Recommended execution order for the actual project work:

1. Update Python package dependencies on PC.
2. Add config for node id, MQTT, and bot-ignore list.
3. Add Telegram filtering for all bot usernames.
4. Add MQTT send/receive implementation.
5. Integrate in main app loop.
6. Add logs and simple tests.
7. Set up Tailscale on both Pi nodes.
8. Set up Mosquitto on Pi A.
9. Deploy updated code to both Pi nodes.
10. Run end-to-end tests on same LAN.
11. Harden MQTT security.
12. Run separated-LAN validation.

## 6. Risks And Countermeasures

### Duplicate playback

Risk:

- bot-originated Telegram voice plus MQTT causes the same message to play twice.

Countermeasure:

- ignore all configured bot usernames in Telegram playback path.

### Message loops

Risk:

- peer playback could trigger a resend cycle if future logic changes.

Countermeasure:

- only local recordings publish to MQTT and send to Telegram.
- never republish Telegram- or MQTT-received audio.

### Broker availability

Risk:

- if Pi A is the broker and goes down, peer transfer stops.

Countermeasure:

- accept this for V2 prototype.
- if needed later, move broker to always-on third host or add fallback broker config.

### Security

Risk:

- anonymous MQTT on a reachable interface is too open.

Countermeasure:

- use anonymous only for first local verification.
- then add password auth and keep traffic inside Tailscale.

## 7. Deliverables For V2

1. Updated Python app with Telegram plus MQTT routing.
2. New env configuration fields documented.
3. Pi setup instructions for Tailscale and Mosquitto.
4. End-to-end test checklist.
5. Service definitions updated if new env variables are added.

## 8. Immediate Next Task

The next implementation step should be:

1. update the Python config model
2. add bot-ignore filtering in Telegram handling
3. add an MQTT handler module
4. wire the MQTT listener/publisher into the app loop

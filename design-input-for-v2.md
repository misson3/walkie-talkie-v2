# telegram walkie talkie version 2 design input

Apr18, 2026, ms

This is for 2 raspberry pi, pi_A and pi_B, to send and receive voice messages.  The messages are also sent to telegram chat group as a log.

Code building and tests will be done with both pi_A and pi_B on the same LAN, but they will be used on separate LAN eventually.

## system overview

**Tailscale:** pi_A, pi_B on separate networks are connected on virtual private network.

**MQTT (Mosquitto):** Taking pi_A (or pi_B) as a broker, mediate the messaging

**Telegram Bot API:** This is used for me (human user) to monitor pi_A, pi_B messages and use this as a message log.  Voice message I (human user) make in this chat group is delivered to pi_A and pi_B.

## implementation logics

###  **When the User (You) Sends a Message**

- **Notification:** The Telegram server sends an "Incoming Message" notification to both bots on pi_A and pi_B simultaneously.
- **Processing:** Both **Bot A** and **Bot B** receive the message as a direct input and execute their respective internal processes (= save the message as a local file in .ogg format, then play it once as already implemented in the current code)

### **2. When Bot A (on pi_A) Performs an Action or Sends a Message**

- **Recording a voice message**: Record message with the record button (on record_pin) press-release action as coded in the current code.  Save it as a .ogg file as in the current code.

- **Post to Telegram:** Bot A uses the `send_message` method to post to the chat group (making it visible to human users).
- **Publish to MQTT:** Simultaneously, Bot A publishes a message to an MQTT topic (e.g., `home/botA/status`) for the other Bot B on pi_B receive it.
- **Bot B’s Response:** **Bot B**, which is monitoring (subscribing to) that MQTT topic, receives the data and triggers the necessary follow-up actions (= save the message as a local file in .ogg format, then play it once as already implemented in the current code)



## steps to build this app

A rough sketch is as follows.

### ステップ1：Tailscaleの導入

1. 両方のRaspberry PiにTailscaleをインストールし、同じアカウントでログインします。
2. 管理画面で、各Raspiに割り振られた **100.x.x.x** 形式のIPアドレスを確認します。

### ステップ2：MQTTブローカーの設定（Raspi Aで行う例）

Raspi Aを「中継サーバー」にします。

Bash

```
sudo apt update
sudo apt install mosquitto mosquitto-clients
```

※外部（Tailscale経由）からの接続を許可するため、`/etc/mosquitto/conf.d/local.conf` を作成し、以下を追記して再起動します。

Plaintext

```
listener 1883
allow_anonymous true
```

### ステップ3：プログラムの実装

Pythonを使用する場合、`python-telegram-bot` などのBotライブラリと、MQTT用の `paho-mqtt` を組み合わせて記述します。
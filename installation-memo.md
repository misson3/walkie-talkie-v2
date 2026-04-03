# installation memo

Mar28, 2026, ms

Trixie Lite (32 bit) on raspi z2w2

Setup Seedstudio respeaker 2 mic hat

```bash
sudo apt update
sudo apt upgrade

reboot
```

```bash
## Install packages
sudo apt install git

# ref:https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/
# I know this is for v2 hat, but just followed apt install part
sudo apt install 
flex bison
libssl-dev
bc
build-essential  # was installed ()12.12), but dependency is upgraded
libncurses5-dev  # libncurses-dev instead
libncursesw5-dev  # livcurses-dev is already the newest
```

```bash
pison@z2w2:~ $ uname -a
Linux z2w2 6.12.75+rpt-rpi-v7 #1 SMP Raspbian 1:6.12.75-1+rpt1 (2026-03-11) armv7l GNU/Linux
pison@z2w2:~ $ uname -r
6.12.75+rpt-rpi-v7

# kernel version is 6.12
```

```bash
# https://github.com/HinTak/seeed-voicecard/tree/v6.12#
change the branch to 6.12
download zip
-> seeed-voicecard-6.12.zip

# cp this to raspi
    ~/Downloads ······················································ 14:05:22  ─╮
❯ scp seeed-voicecard-6.12.zip z2w2:/home/pison                                        ─╯
Enter passphrase for key '/c/Users/mitsu/.ssh/to_z2w2/key-to-z2w2':
seeed-voicecard-6.12.zip                                100%  796KB   3.5MB/s   00:00
```

```bash
# raspi side
# pison@z2w2 上で
unzip seeed-voicecard-6.12.zip
cd seeed-voicecard-6.12/
sudo ./install.sh

# git branch name masterについて何か言われるが、repoとして使わないので気にしない。

reboot
```

```bash
pison@z2w2:~ $ aplay -l
**** List of PLAYBACK Hardware Devices ****
card 0: vc4hdmi [vc4-hdmi], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0

# Hatつけてない状態。ここでshutdownしてhatをつけて起動する。
sudo shutdown -h now

# hatつけて起動。
```

```bash
pison@z2w2:~ $ aplay -l
**** List of PLAYBACK Hardware Devices ****
card 0: vc4hdmi [vc4-hdmi], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: seeed2micvoicec [seeed-2mic-voicecard], device 0: bcm2835-i2s-wm8960-hifi wm8960-hifi-0 [bcm2835-i2s-wm8960-hifi wm8960-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0

pison@z2w2:~ $ arecord -l
**** List of CAPTURE Hardware Devices ****
card 1: seeed2micvoicec [seeed-2mic-voicecard], device 0: bcm2835-i2s-wm8960-hifi wm8960-hifi-0 [bcm2835-i2s-wm8960-hifi wm8960-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
 
よさそう。
```

```bash
pison@z2w2:~ $ arecord -D hw:1,0 -f cd -d 15 -t wav test.wav
Recording WAVE 'test.wav' : Signed 16 bit Little Endian, Rate 44100 Hz, Stereo

# 動いたっぽい。

pison@z2w2:~ $ ls
seeed-voicecard-6.12  seeed-voicecard-6.12.zip  test.wav

pison@z2w2:~ $ aplay -D hw:1,0 test.wav
Playing WAVE 'test.wav' : Signed 16 bit Little Endian, Rate 44100 Hz, Stereo

# すげえ割れてるが、録音、再生できた。

```

```bash
alsamixer
F6

どれをどう触ればいいのかよくわかってないが、それらしいところから試す。

Speaker3つ見える。83<>83, 80, 80にしてみる
Pleybackも83<>83


あとはそのまま。

いろいろやったが、このぐらいにしとけばいいという設定は以下の通り

Speaker 100でいい。AC, DCってやつは増やしても何も変わらないかんじなので、0にしとく。
Left, Right Input Boost Mixer LINPUT1を57に。このうえは100になって割れる。

Playback　100。変えても変わらん感じ
```

```bash
まとめると、
Speaker 100
Input Mixer INPUT1 57

なのだが、次の起動時にはこの設定が消えてしまう。
どうやって保存するかをしらべた。
以下のようにすれば、保存、再読出しができる。

alsactl --file ~/.config/asound.state store
alsactl --file ~/.config/asound.state restore

sudo alsactl sotreとすればsystem wideに次の起動時に読まれると
https://askubuntu.com/questions/50067/how-to-save-alsamixer-settings
がいってるんだが、そうはならなかった。

ので、上のようにhomeに書き込んで、二番目をcrontabで起動後に走らせる。ここで、カードの存在をsystemが知ってからコマンドを走らせないと失敗する。crontabでは起動後30秒まってから動くようにした。

@reboot sleep 30 && /usr/sbin/alsactl --file ~/.config/asound.state restore

geminiがいうにはsystemdとしてsound.tartetの後に読ませるようにするとよりproのやりかた、というんだが、crontabのほうが簡単なのでそうした。うまくいくsleep durationをみつければいいわけだし。
```

```bash
sudo systemctl list-units --type=service
で一覧出せる。
sudo systemctl status seeed-voicecard.service
でstatusを見る。
```

ここまででマイクとスピーカーを使えるようになった。

あとは、on board LEDとbuttonを使えるようにしたい。

https://github.com/respeaker/mic_hat

にexample codeがある。BottonはPIN 17, LEDはapa102.py(spidevが必要)にクラスが定義されている。



**Mar29, 2026**

構築にとりかかる。

uvをNZXTにいれた。

z2w2にも入れた。

まずは、LEDとbutton controlができるようにする。

uv add spidevでPython.hがないエラー。どっかでみたよな、これ。昨日出るかと思ったんだが昨日はこれ関連のエラーなかった。geminiにきいて、

```bash
sudo apt update
sudo apt install python3-dev
で
uv add spidev
とおった。

uv add Rpi.GPIO

```



**Apr03, 2026**

コードはgh copilotがほぼ書き終わり。pi上でのテストに入りたい。

Raspberry pi 上での準備

環境変数設定の仕方について聞いてみた。.bashrc?

I will follow your steps 1, 2, 3 on Pi. Before that, I need to add bot token and chat id to my environmental variable. I want to make it permanent on this raspberry pi. What is the good practice to store them? I guess ~/.bashrc would be good rather than in a file in the project folder.

Good question. ~/.bashrc is convenient, but not best practice for this case.

Best practice on Raspberry Pi
1. Store secrets in a dedicated env file outside the project folder.
2. Restrict file permission to owner-only.
3. Load that file from systemd if you run the app as a service.
4. Optionally source it in your shell for manual runs.

Why not ~/.bashrc
1. It only applies to interactive bash sessions.
2. It will not reliably apply to systemd services.
3. You are also using zsh, so it is easy to get inconsistent behavior.

Recommended setup
1. Create a secure folder and env file:
sudo install -d -m 700 /etc/walkie-talkie
sudo nano /etc/walkie-talkie/walkie-talkie.env

2. Put values in it:
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_CHAT_ID
TELEGRAM_PEER_BOT_USERNAME=koe2_bot
AUDIO_DEVICE=hw:1,0
GPIO_RECORD_PIN=12
GPIO_REPLAY_PIN=17
GPIO_RECORD_ACTIVE_LOW=true
GPIO_REPLAY_ACTIVE_LOW=true

3. Lock it down:
sudo chmod 600 /etc/walkie-talkie/walkie-talkie.env
sudo chown root:root /etc/walkie-talkie/walkie-talkie.env

Manual run from terminal
1. Load env then run:
set -a
source /etc/walkie-talkie/walkie-talkie.env
set +a
python main.py

If you use systemd (recommended)
1. In your service unit, include:
EnvironmentFile=/etc/walkie-talkie/walkie-talkie.env

This is the cleanest permanent approach for production-like operation on Pi.

If you want, I can generate a ready-to-use systemd service file next.





the command
source /etc/walkie-talkie/walkie-talkie.env
gives permission error. Because it is set 600. Relax the permission or use sudo here?

Good catch. For manual runs as a regular user, you have two options:

**Option 1: Relax system file permissions (simpler for now)**
```bash
sudo chmod 640 /etc/walkie-talkie/walkie-talkie.env
```
This allows owner to read/write, group to read. Your user can now source it.

**Option 2: Use a user-scoped env file (more practical for testing)**
Since you're testing manually, put it in your home directory instead:
```bash
install -d -m 700 ~/.walkie-talkie
nano ~/.walkie-talkie/walkie-talkie.env
# Add your secrets
chmod 600 ~/.walkie-talkie/walkie-talkie.env
```

Then source it:
```bash
set -a
source ~/.walkie-talkie/walkie-talkie.env
set +a
python main.py
```

**My recommendation**
1. Use Option 2 now for manual testing on your own account.
2. Once you confirm everything works and switch to systemd service, move to the system-wide `/etc/walkie-talkie/` folder with strict 600 permission (systemd will run as root and can read it).

This keeps secrets out of your shell history and project folder, but is still convenient for development.



OPTION2でまずは。

```bash
python hardware_smoke_test.py --seconds 20
```

でボタンはうまく動くこと確認できた。緑もつくし、ボタン押したときは赤がつく。





I ran
python hardware_smoke_test.py --seconds 20
and button looks working.
What is the next step? I want to confirm if the audio is recorded in ogg format.



Great! Now let's test audio recording and verify OGG format. I'll create a quick audio smoke test script that records a short clip and verifies it. 

Created [](file:///c%3A/Users/mitsu/Desktop/z2w2-walkie-talkie-Mar28-2026/audio_smoke_test.py)

Apply Patch

Replacing 7 lines with 25 lines in [](file:///c%3A/Users/mitsu/Desktop/z2w2-walkie-talkie-Mar28-2026/README.md)


```

```
Done. I created audio_smoke_test.py for you to test audio recording and format validation.

**What the script does:**
1. Records 5 seconds of audio from the Re-speaker HAT microphone
2. Saves to `/tmp/audio_smoke_test.ogg` in OGG/Opus format
3. Checks file size and format using `file` command
4. Optionally runs `ffprobe` for detailed codec info

**Run it:**
```bash
set -a
source ~/.walkie-talkie/walkie-talkie.env
set +a
python audio_smoke_test.py --seconds 5
```

**What to expect:**
- Output file created at `/tmp/audio_smoke_test.ogg`
- File size should be > 0 bytes (typically 5-10 KB for 5 seconds)
- `file` output should show OGG/Vorbis or Opus format
- You can then manually playback: `aplay -D hw:1,0 /tmp/audio_smoke_test.ogg`

If that passes, you're ready to run the full app:
```bash
python main.py
```

Then test end-to-end: press Button A to record, Button B to playback, and monitor Telegram group for uploaded messages.

Made changes.



ffmpegがない。

```bash
sudo apt update
sudo apt install ffmpeg
```



















https://github.com/respeaker/mic_hat/tree/master

のcodeを少し試す。pyaudio入れからてこずる。

```bash
mkdir python-test
cd python-test
python -m venv env
source ./env/bin/activate

で、requirementsにあるspidevをいれようとしてひっかかる。Python.hがないといっている。
なにかがたりていない。
google how to build pyaudio on raspberry pi

sudo apt install build-essential  # already installed
sudo apt install python3-dev

でようやく。
pip install spidevとおった。
つづける
pip install rpi.gpio
pip install pyaudio
pip install numpy

record.pyはうごいた。
arecordはCard3というのだが、
REAPEAKER_INDEX = 1
で動く。一つ目だからか。
まあいいや。
```


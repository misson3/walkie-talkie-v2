# raspi setup memo

Mar28, 2026, ms

OS: Trixie Lite (32 bit)

Setup Seeedstudio respeaker 2-mic hat

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
uname -a
Linux z2w2 6.12.75+rpt-rpi-v7 #1 SMP Raspbian 1:6.12.75-1+rpt1 (2026-03-11) armv7l GNU/Linux
uname -r
6.12.75+rpt-rpi-v7

# kernel version is 6.12
```

```bash
# これPC側。
# https://github.com/HinTak/seeed-voicecard/tree/v6.12#
change the branch to 6.12
download zip
-> seeed-voicecard-6.12.zip

# cp this to raspi
scp seeed-voicecard-6.12.zip <destination dir on your raspi>
```

```bash
# raspi sideに戻って。
unzip seeed-voicecard-6.12.zip
cd seeed-voicecard-6.12/
sudo ./install.sh

# git branch name masterについて何か言われるが、repoとして使わないので気にしない。

# Hatつけてない状態。ここでshutdownしてhatをつけて起動する。
sudo shutdown -h now
```

```bash
aplay -l
**** List of PLAYBACK Hardware Devices ****
card 0: vc4hdmi [vc4-hdmi], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: seeed2micvoicec [seeed-2mic-voicecard], device 0: bcm2835-i2s-wm8960-hifi wm8960-hifi-0 [bcm2835-i2s-wm8960-hifi wm8960-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0

arecord -l
**** List of CAPTURE Hardware Devices ****
card 1: seeed2micvoicec [seeed-2mic-voicecard], device 0: bcm2835-i2s-wm8960-hifi wm8960-hifi-0 [bcm2835-i2s-wm8960-hifi wm8960-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
 
# よさそう。
```

```bash
# recording test
arecord -D hw:1,0 -f cd -d 15 -t wav test.wav
Recording WAVE 'test.wav' : Signed 16 bit Little Endian, Rate 44100 Hz, Stereo

# play test
aplay -D hw:1,0 test.wav
Playing WAVE 'test.wav' : Signed 16 bit Little Endian, Rate 44100 Hz, Stereo

# すげえ割れてるが、録音、再生できた。
```

```bash
alsamixer
# F6でサウンドカード選ぶ。

# あれこれ設定を変えて、声が割れないようなものを探る。
まとめると、
Speaker 100
Input Mixer INPUT1 57

でよさそうなのだが、次の起動時にはこの設定が消えてしまう。
どうやって保存するかをしらべた。

alsactl --file ~/.config/asound.state store
alsactl --file ~/.config/asound.state restore

sudo alsactl sotreとすればsystem wideに次の起動時に読まれると
https://askubuntu.com/questions/50067/how-to-save-alsamixer-settings
がいってるんだが、そうはならなかった。

そこで、上のように~/.config/asound.stateに書き込んで、二番目のrestoreのほうをcrontabで起動後に走らせる。ここで、カードの存在をsystemが知ってからコマンドを走らせないと失敗する。crontabでは起動後30秒まってから動くようにした。

@reboot sleep 30 && /usr/sbin/alsactl --file ~/.config/asound.state restore

geminiがいうにはsystemdとしてsound.tartetの後に読ませるようにするとよりproのやりかた、というんだが、crontabのほうが簡単なのでそうした。うまくいくsleep durationをみつければいいわけだし。
```

```bash
# そのほかコマンドメモ
sudo systemctl list-units --type=service
で一覧出せる。
sudo systemctl status seeed-voicecard.service
でstatusを見る。
```

ここまででマイクとスピーカーを使えるようになった。

あとは、on board LEDとbuttonを使えるようにしたい。

https://github.com/respeaker/mic_hat

にexample codeがある。ButtonはPIN 17, LEDはapa102.py(spidevが必要)にクラスが定義されている。



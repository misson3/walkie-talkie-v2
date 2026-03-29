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


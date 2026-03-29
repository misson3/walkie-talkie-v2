# telegram walkie talkie design input

Mar29, 2026, ms

## What is this?

This is a python application with telegram bot, running on raspberry pi zero 2 W.



## What does this do?

Two telegram bots, koe1_bot and koe2_bot, are in a chat group with a few human members.  The program I am going to build is written in python and koe1_bot is a worker in the application.  This application is deployed on raspberry pi zero 2 W, connected to my house wifi LAN.  Two buttons, button A and B, are connected to GPIO of the raspberry pi.  See the GPIO pin number in following section.

When the button A is pressed, sound recording is started.  When the button A is pressed again, the recording is stopped and an audio file is saved.  The file format is preferred to be .ogg.  If the recording is not saved directly in .ogg format, it can be saved in other format like .wav, then converted into .ogg format.  The saved .ogg file is sent to the chat group by the koe1_bot.  The file name is always "to-go-voice.ogg" so that there is always a single record file.

When a sound file is sent to the chat group by the other bot, koe2_bot, koe1_bot will download it and play the message to a speaker connected to the raspberry pi zero 2 W.  The downloaded file is always named as "to-play-voice.ogg" so that there is always a single downloaded file.

When the button B is pressed, the downloaded file, "to-play-voice.ogg" will be played again.

The same thing will be performed by koe2_bot on another raspberry pi zero 2.  I will do this test in the same hose hold, but it will be placed in other LAN in the other side of the house.



## Hardware connected to the raspberry pi zero 2

Re-speaker 2-mic pi hat is mounted on the raspberry pi zero 2 W.  The hat has 2 microphones on the board and a speaker is connected to the hat.  Recording and playing were tested with `arecord` and `aplay` commands as follows.

`arecord -D hw:1,0 -f cd -d 15 -t wav test.wav`

`aplay -D hw:1,0 test.wav`

Test file is in .wav format and I learned that the file should be in .ogg format to be sent on the telegram.

The button A is connected on GPIO 12 with pull up circuit I prepared.  The button B is on GPIO 17 on the HAT and it is configured as pull up according to the diagram in  `ReSpeaker 2-Mics Pi HAT_SCH.pdf`.

The HAT also has 3 color LEDs, which is called APA102 or dot star (?), which is controlled with SPI on the raspberry pi.  See the reference code mentioned in the next section.



## Reference codes for the LEDs and button

The on board LED control class is defined as APA102 class in `apa102.py`.   The public methods are listed in the class APA102 docstring.

Button usage for the button B is written in `button.py`  



## LED control

There are 3 LEDs on the HAT.  I want to allocate following roles to each LEDs.

**LED1**

- Turn on with green when the application starts, turn off when the application ends.

**LED2**

- Turn on with red when the recording is on going.  Turn off when the recording is done.

**LED3**

- Turn on blue when a downloaded file is playing.  Turn off when the play is completed.



## Other requirement

I prefer to have the main code written in python, but if other command line tools are available and more efficient than doing a certain tasks, call the tool from  the python main code, rather than implementing it in python.



 





 
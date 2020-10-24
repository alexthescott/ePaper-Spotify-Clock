# 4.2in E-Paper Spotify Weather Clock 
This project uses Python3 to display [two](https://open.spotify.com/user/bassguitar1234?si=hHnnqHUGTe25liNezp9cJQ) [users'](https://open.spotify.com/user/ermisk?si=0G5DmMxCRLuUm1G6-EWhFA) recent Spotify history, weather for two cities (local and away), and the current time 

<p align="center">
	<img src="spotify_epaper_preview.jpg" width="400">
	<img src="spotify_epaper_preview2.jpg" width="400">
</p>

Written for [Waveshare's 4.2 e-paper display](https://www.waveshare.com/4.2inch-e-paper.htm), this project connects with Spotify's API to display the most recent listening information, including the title, artist, context, and time since the track was played. There is a left and right panel so that two folk's listening can be displayed at the same time. The forcast and current weather are also displayed via the OpenWeatherMap api. The e-paper display updates in full every 3 minutes per Waveshare's recommendations. After 8pm, the display updates every 5 minutes, and does not update from 2am - 6am. Open invite to email me, atscott@ucsc.edu, if you have any questions regarding my implementation, or suggestions to improve this project. Before you ask, I am using the Nintendo DS BIOS font for this project because it looks beautiful.

### ⌛ Quick Overview 
Waveshare provides a set of [instructions](https://www.waveshare.com/wiki/4.2inch_e-Paper_Module) under the Hardware/Software setup tab to install the libraries required to drive the display. I'm using a [Raspberry Pi Zero W](https://www.raspberrypi.org/products/raspberry-pi-zero-w/) running this [bash script](https://github.com/alexthescott/ePaper-Spotify-Clock/blob/master/launch_epaper.sh) in [rc.local](https://www.raspberrypi.org/documentation/linux/usage/rc-local.md) to run [mainSpotifyClock.py](https://github.com/alexthescott/ePaper-Spotify-Clock/blob/master/mainSpotifyEPD.py). Three custom Python modules were used, [Spotipy](https://spotipy.readthedocs.io/en/2.12.0/), [Requests](https://requests.readthedocs.io/en/master/), and [Pillow aka PIL](https://pillow.readthedocs.io/en/stable/), all of which can be installed using [Pip](https://pip.pypa.io/en/stable/)

Drive the EPD, call necessary functions -> [mainSpotifyEPD.py](https://github.com/alexthescott/ePaper-Spotify-Clock/blob/master/mainSpotifyEPD.py)

Write to Pillow Image Object -> [drawToEPD.py](https://github.com/alexthescott/ePaper-Spotify-Clock/blob/master/drawToEPD.py)

Write to a local .txt JSON file for contextual info -> [localJsonIO.py](https://github.com/alexthescott/ePaper-Spotify-Clock/blob/master/localJsonIO.py)

Image and Front Resources -> [Icons](https://github.com/alexthescott/ePaper-Spotify-Clock/tree/master/Icons) and [Fonts](https://github.com/alexthescott/ePaper-Spotify-Clock/tree/master/ePaperFonts) 
 
### ⏳ Full Instillation Guide 
1) In the 'Hardware/Software setup' tab of Waveshare's [4.2inch wiki](https://www.waveshare.com/wiki/4.2inch_e-Paper_Module), use the GPIO guide to attach the display to the Pi
2) Enable SPI interface by launching raspi-config, choosing 'Interfacing Options', 'SPI', Yes to enable SPI interface
```bash
sudo raspi-config
```
3) Install Python libraries
```bash
sudo apt-get update
sudo apt-get install python3-pip
sudo apt-get install python3-pil
sudo apt-get install python3-numpy
sudo pip3 install RPi.GPIO
sudo pip3 install spidev
```
3) Download Waveshare Examples and Python Libraries
```bash
sudo git clone https://github.com/waveshare/e-Paper
```
4) Navigate to Pi/Python folder, and Install 'waveshare-epd' Python module from setup.py
```bash
cd e-Paper/RaspberryPi\&JetsonNano/python
sudo python3 setup.py install
```
5) Navigate to Pi/Python/examples folder, and run the Waveshare's provided example file to make sure the wiring is correct
```bash
cd examples
sudo python3 epd4in2.py
```
6) Clone this repository into the examples folder 
```bash
sudo git clone https://github.com/alexthescott/ePaper-Spotify-Clock
```
7) Move the [launch_epaper.sh](https://github.com/alexthescott/ePaper-Spotify-Clock/blob/master/launch_epaper.sh) file into your home directory, then edit its contents to match your username

### APIs 
[Openweathermap](https://openweathermap.org/api) gets the current weather and forcast, and the [Spotipy](https://github.com/plamere/spotipy) wrapper interfaces with Spotify's API

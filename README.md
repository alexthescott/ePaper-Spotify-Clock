# RaspberryPi E-Paper Spotify Clock
## TLDR: Desktop clock to help read/see Spotify listening info

<p align="center">
	<img src="spotify_epaper_preview.png" width="400">
	<img src="spotify_epaper_preview2.png" width="400">
</p>

### 🕰️ Quick Project Overview
Python + Bash with a Raspberry Pi and [Waveshare's 4.2 ePaper display](https://www.waveshare.com/product/4.2inch-e-paper-module.htm) and ePaper library, using [Spotipy](https://spotipy.readthedocs.io/en/2.22.1/) for track info, [OpenWeathermap](https://openweathermap.org/) for weather info, and [Pillow](https://pillow.readthedocs.io/en/stable/) to generate/display image.

### ⌛ Install Guide
- We presume you have a headless Raspberry Pi (I use a Zero W 2) with Waveshare's 4.2inch ePaper display attached via GPIO.
- Waveshare provides a set of [instructions](https://www.waveshare.com/wiki/4.2inch_e-Paper_Module_Manual#Working_With_Raspberry_Pi) in the 'Hardware/Software' setup tab under the setup tab to install the libraries required to drive the display, follow that guide, enable SPI interface in raspi-config, and install the software below as su. 
	- ```bash
		sudo apt-get install git python3-pip python3-pil python3-numpy imagemagick
		sudo pip3 install RPi.GPIO spidev spotipy requests
- Clone Waveshare Examples and Python Libraries, install setup.py and test epd_4in2_test.py
	- ```bash
		sudo git clone https://github.com/waveshare/e-Paper
		cd e-Paper/RaspberryPi\&JetsonNano/python
		sudo python3 setup.py install
		cd examples
		sudo python3 epd_4in2_test.py
- Clone this repository, and alter config/keys.json to include one or two Spotify User's id and secret generated from [Spotify's Create App page](https://developer.spotify.com/dashboard) and a free [OpenWeatherMap token](https://home.openweathermap.org/api_keys)
- Run main.py and pass in returned google url into terminal to sync Spotify key to project.
- Modify e-Paper/launch_epaper.sh to point to the correct main.py path.
- call ./launch_epaper.sh on reboot via cron or rc.local

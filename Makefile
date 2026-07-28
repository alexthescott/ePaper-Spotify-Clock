REPO_DIR := $(shell pwd)
VENV := $(REPO_DIR)/.venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
WAVESHARE_DIR := $(HOME)/e-Paper

UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)
ON_PI := $(shell [ "$(UNAME_S)" = "Linux" ] && echo yes || echo no)

.PHONY: setup venv deps system-deps waveshare configs systemd local-test clean

# Full first-time setup. Safe to re-run.
setup: venv deps waveshare configs systemd
	@echo "Setup complete. Edit config/keys.json, then run 'python3 main.py --local' once per user to complete Spotify OAuth before starting the service."

venv:
	@test -d $(VENV) || python3 -m venv $(VENV)

deps: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# System packages needed by Pillow/imagemagick dithering/the waveshare lib.
# RPi.GPIO/spidev are intentionally NOT in requirements.txt: they're
# hardware-linked packages that need to build against the Pi's system
# libraries, so they're installed here (and by the waveshare target)
# rather than into the venv on non-Pi dev machines.
system-deps:
ifeq ($(ON_PI),yes)
	sudo apt-get update
	sudo apt-get install -y git python3-pip python3-pil python3-numpy imagemagick python3-venv
	$(PIP) install RPi.GPIO spidev
else
	@echo "Skipping system-deps: not running on Linux (ON_PI=$(ON_PI)). Run this target on the Pi."
endif

# Clones and installs Waveshare's e-Paper driver library, which is not
# published on PyPI and must come straight from their repo.
waveshare:
ifeq ($(ON_PI),yes)
	@if [ ! -d $(WAVESHARE_DIR) ]; then \
		git clone --depth 1 https://github.com/waveshare/e-Paper.git $(WAVESHARE_DIR); \
	else \
		echo "$(WAVESHARE_DIR) already exists, skipping clone"; \
	fi
	cd $(WAVESHARE_DIR)/RaspberryPi_JetsonNano/python && $(PIP) install .
else
	@echo "Skipping waveshare: not running on Linux (ON_PI=$(ON_PI)). Run this target on the Pi."
endif

# Copies config templates into place without ever overwriting real,
# user-populated config files.
configs:
	@[ -f config/keys.json ] || cp config/keys.json.example config/keys.json
	@echo "Config templates in place. Edit config/keys.json with your Spotify + OpenWeatherMap credentials."

# Generates and installs the systemd unit, then enables (but does not
# start) it — first run needs interactive Spotify OAuth, see 'setup'.
systemd:
ifeq ($(ON_PI),yes)
	sed -e 's|__USER__|$(shell whoami)|' -e 's|__REPO_DIR__|$(REPO_DIR)|' \
		systemd/epaper-clock.service.template | sudo tee /etc/systemd/system/epaper-clock.service > /dev/null
	sudo systemctl daemon-reload
	sudo systemctl enable epaper-clock.service
	@echo "epaper-clock.service installed and enabled. Complete first-run OAuth, then: sudo systemctl start epaper-clock"
else
	@echo "Skipping systemd: not running on Linux (ON_PI=$(ON_PI)). Run this target on the Pi."
endif

# Renders one frame locally (no EPD hardware required) for dev/testing.
local-test: deps
	$(PYTHON) main.py --local

clean:
	rm -rf $(VENV)

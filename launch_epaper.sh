#!/bin/sh
# launch_epaper.sh
# navigate to directory then execute python script 

runscript(){
	python3 spotify_epd.py
}

cd /home/alex/e-Paper/Pi/python/examples/
while true; 
do
	runscript
	sleep 3m 
done

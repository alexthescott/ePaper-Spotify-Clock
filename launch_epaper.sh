#!/bin/sh
# launch_epaper.sh
# navigate to directory then execute python script 

runscript(){
	python3 mainSpotifyClock.py
}

cd /home/{USER}/e-Paper/Pi/python/examples/
while true; 
do
	runscript
	sleep 3m 
done

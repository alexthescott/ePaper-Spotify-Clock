#!/bin/sh
# launch_epaper.sh
# navigate to directory then execute python script 

runscript(){
	python3 mainSpotifyClock.py 2>> failures.txt
	echo "Failure occurred at: $(date '+%Y-%m-%d %H:%M:%S')" >> failures.txt
	echo "" >> failures.txt
}

cd /home/{USER}/e-Paper/Pi/python/examples/
while true; 
do
	runscript
    sleep 1m 
done
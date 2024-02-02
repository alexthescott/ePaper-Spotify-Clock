#!/bin/sh
# launch_epaper.sh
# navigate to directory then execute python script 
ePaperClockLocation="/home/$USER/e-Paper/RaspberryPi_JetsonNano/python/examples/"

runscript(){
    if ! pgrep -f "python3 mainSpotifyClock.py" > /dev/null
    then
        python3 mainSpotifyClock.py 2>> failures.txt
        if [ $? -ne 0 ]; then
            echo -e "Failure occurred in mainSpotifyClock.py at: $(date '+%Y-%m-%d %H:%M:%S')\n" >> failures.txt
        fi
    fi
}

cd $ePaperClockLocation
while true; 
do
	runscript
    sleep 1m 
done
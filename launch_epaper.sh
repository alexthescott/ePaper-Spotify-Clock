#!/bin/sh
# launch_epaper.sh
# navigate to directory then execute python script
ePaperClockLocation="/home/$USER/e-Paper/RaspberryPi_JetsonNano/python/examples/"

# Initialize our own variables
verbose=0
clock=0
local=0

# Parse command-line arguments
while (( "$#" )); do
  case "$1" in
  -v | --verbose)
    verbose=1
    shift
    ;;
  --clock)
    clock=1
    shift
    ;;
  --local)
    local=1
    shift
    ;;
  *)
    echo "Error: Invalid option"
    exit 1
    ;;
  esac
done

runscript() {
  if ! pgrep -f "python3 mainSpotifyClock.py" >/dev/null; then
    # Construct the python command with the parsed arguments
    python_cmd="python3 mainSpotifyClock.py"
    [ "$verbose" = 1 ] && python_cmd="$python_cmd -v"
    [ "$clock" = 1 ] && python_cmd="$python_cmd --clock"
    [ "$local" = 1 ] && python_cmd="$python_cmd --local"

    echo "Running command: $python_cmd"
    if [ "$verbose" = 1 ]; then
      $python_cmd
    else
      $python_cmd 2>>failures.txt
    fi
    if [ $? -ne 0 ]; then
      echo -e "Failure occurred in mainSpotifyClock.py at: $(date '+%Y-%m-%d %H:%M:%S')\n" >>failures.txt
    fi
  fi
}

cd $ePaperClockLocation
while true; do
  runscript
  sleep_duration=60
  echo "Sleeping for $sleep_duration seconds"
  sleep $sleep_duration
  sleep 60
done

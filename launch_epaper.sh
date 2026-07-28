#!/bin/bash
# launch_epaper.sh
# Single-shot runner for main.py, intended to be invoked by systemd
# (systemd's Restart=on-failure/RestartSec= owns the retry loop).
cd "$(dirname "$(readlink -f "$0")")" || exit 1

# Initialize our own variables
verbose=0
clock=0
local_run=0

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
  --local_run)
    local_run=1
    shift
    ;;
  *)
    echo "Error: Invalid option"
    exit 1
    ;;
  esac
done

rotate_failures() {
  # Cap failures.txt at ~2MB. Keep one previous (.1), drop older (.2).
  local f="failures.txt"
  local max_bytes=$((2 * 1024 * 1024))
  if [ -f "$f" ]; then
    local size
    size=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo 0)
    if [ "$size" -ge "$max_bytes" ]; then
      [ -f "$f.1" ] && mv "$f.1" "$f.2"
      mv "$f" "$f.1"
      : > "$f"
    fi
  fi
}

runscript() {
  rotate_failures
  if ! pgrep -f "python3 main.py" >/dev/null; then
    # Construct the python command with the parsed arguments
    python_cmd="python3 main.py"
    [ "$verbose" = 1 ] && python_cmd="$python_cmd -v"
    [ "$clock" = 1 ] && python_cmd="$python_cmd --clock"
    [ "$local_run" = 1 ] && python_cmd="$python_cmd --local"

    echo "Running command: $python_cmd"
    if [ "$verbose" = 1 ]; then
      $python_cmd
    else
      $python_cmd 2>>failures.txt
    fi
    if [ $? -ne 0 ]; then
      echo -e "Failure occurred in main.py at: $(date '+%Y-%m-%d %H:%M:%S')\n" >>failures.txt
      exit 1
    fi
  fi
}

runscript

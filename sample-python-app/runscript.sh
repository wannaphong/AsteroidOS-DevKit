#!/bin/sh
export PYTHONPATH="/usr/share/asteroid-pycounter:$PYTHONPATH"
exec python3 /usr/share/asteroid-pycounter/main.py "$@"


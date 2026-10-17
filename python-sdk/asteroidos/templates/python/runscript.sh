#!/bin/sh
export PYTHONPATH="/usr/share/{{ app_name }}:$PYTHONPATH"
exec python3 /usr/share/{{ app_name }}/main.py "$@"


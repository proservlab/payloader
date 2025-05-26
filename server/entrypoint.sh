#!/bin/bash

SCRIPTNAME="$(basename "$0")"
SHORT_NAME="${SCRIPTNAME%.*}"
SCRIPT_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
SCRIPT_DIR="$(basename $SCRIPT_PATH)"
VERSION="0.0.1"

# set current working directory to the script directory
cd $SCRIPT_PATH

if [ -z $HOST ]; then
    # HOST=$(curl -s https://ipv4.icanhazip.com)
    HOST=$(hostname -I | awk '{print $1}')
fi

if [ -z $PORT ]; then
    PORT=4444
fi

python3 server.py --port="$PORT" --host="$HOST"
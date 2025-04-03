#!/bin/bash

SCRIPTNAME="$(basename "$0")"
SHORT_NAME="${SCRIPTNAME%.*}"
SCRIPT_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
SCRIPT_DIR="$(basename $SCRIPT_PATH)"
VERSION="1.1.2"

# set current working directory to the script directory
cd $SCRIPT_PATH

export CONTAINER_NAME="reverse_client_2_$(openssl rand -hex 4)"
export SERVER_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' reverse_server_2)"
docker run -it --rm --name $CONTAINER_NAME -v $(pwd)/tmp:/tmp -e SERVER_IP=$SERVER_IP -e SERVER_PORT=4444 reverse_client_2
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

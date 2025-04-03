#!/bin/bash

SCRIPTNAME="$(basename "$0")"
SHORT_NAME="${SCRIPTNAME%.*}"
SCRIPT_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
SCRIPT_DIR="$(basename $SCRIPT_PATH)"
VERSION="1.1.2"

# set current working directory to the script directory
cd $SCRIPT_PATH

docker stop reverse_server_2
docker rm reverse_server_2
# assume osx is docker to docker testing no need to override ip
if [[ $(uname -s) == "Darwin" ]]; then
docker run -v $(pwd)/files:/app/files --rm --name reverse_server_2 -p 4444:4444 -p 4445:4445 reverse_server_2
# assume linux is external to docker but local network (there is a 3rd case for external network but not covered here)
elif [[ $(uname -s) == "Linux" ]]; then
docker run -v $(pwd)/files:/app/files --rm -e HOST=$(hostname -I | awk '{print $1}') --name reverse_server_2 -p 4444:4444 -p 4445:4445 reverse_server_2
fi
docker stop reverse_server_2
docker rm reverse_server_2
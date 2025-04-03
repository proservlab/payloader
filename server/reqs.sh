#!/bin/bash

SCRIPTNAME="$(basename "$0")"
SHORT_NAME="${SCRIPTNAME%.*}"
SCRIPT_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
SCRIPT_DIR="$(basename $SCRIPT_PATH)"
VERSION="0.0.1"

# set current working directory to the script directory
cd $SCRIPT_PATH

python3 -m pip install pipreqs
python3 -m pipreqs.pipreqs --encoding utf-8 --force
echo "python-multipart" >> requirements.txt
python3 -m pip install -r requirements.txt
#! /bin/bash

BUNDLE_VERSION=$1
BUNDLE_NAME="moxaiiot-ciss-to-tpg_v$BUNDLE_VERSION.tgz"

chmod +x "exec"

BUNDLE_CONTENT=(

exec 
ciss_to_tpg.py
sensor.json
sensor_all.json
LICENSE
README.md
lib/*

)

tar -czf $BUNDLE_NAME ${BUNDLE_CONTENT[*]}
if [ $? -ne 0 ] ; then
    echo "Failed to build $BUNDLE_NAME"
    exit -1
fi
echo "Successful build $BUNDLE_NAME"
exit 0

#!/bin/bash
set -e

NW=/home/samuel/fabric-iot-ids/fabric-samples/test-network
KEYSTORE=$NW/organizations/peerOrganizations/org1.example.com/users/User1@org1.example.com/msp/keystore
KEYFILE=$(ls $KEYSTORE)

echo "Key file: $KEYFILE"

# Copy connection profile
cp /mnt/e/My_Projects/Mini\ Project/explorer_config/connection-profile/test-network.json \
   /home/samuel/hlf-explorer/examples/net1/connection-profile/test-network.json

# Patch actual key filename
sed -i "s|priv_sk|$KEYFILE|g" \
   /home/samuel/hlf-explorer/examples/net1/connection-profile/test-network.json

echo "Connection profile updated:"
grep keystore /home/samuel/hlf-explorer/examples/net1/connection-profile/test-network.json

# Check the config.json in net1
cat /home/samuel/hlf-explorer/examples/net1/config.json

#!/bin/bash
set -e

cd /home/samuel/hlf-explorer

export EXPLORER_CONFIG_FILE_PATH=/home/samuel/hlf-explorer/examples/net1/config.json
export EXPLORER_PROFILE_DIR_PATH=/home/samuel/hlf-explorer/examples/net1/connection-profile
export FABRIC_CRYPTO_PATH=/home/samuel/fabric-iot-ids/fabric-samples/test-network/organizations

echo "Config:  $EXPLORER_CONFIG_FILE_PATH"
echo "Profile: $EXPLORER_PROFILE_DIR_PATH"
echo "Crypto:  $FABRIC_CRYPTO_PATH"

# Stop any previous instance cleanly
docker-compose -f docker-compose.yaml down -v 2>/dev/null || true

# Start fresh
docker-compose -f docker-compose.yaml up -d

echo ""
echo "Waiting 40s for database to be healthy..."
sleep 40

echo ""
echo "=== Running containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Explorer logs (last 20 lines) ==="
docker logs explorer.mynetwork.com --tail 20 2>&1 || echo "Explorer container not found"

echo ""
echo "Explorer UI: http://localhost:8080"
echo "Login: exploreradmin / exploreradminpw"

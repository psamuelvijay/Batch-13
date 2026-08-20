#!/bin/bash
export PATH=/home/samuel/fabric-iot-ids/fabric-samples/bin:$PATH
export FABRIC_CFG_PATH=/home/samuel/fabric-iot-ids/fabric-samples/config/
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID=Org1MSP
NW=/home/samuel/fabric-iot-ids/fabric-samples/test-network
export CORE_PEER_TLS_ROOTCERT_FILE=$NW/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=$NW/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=localhost:7051

echo "=== Testing getRecordCount ==="
peer chaincode query -C mychannel -n idsaudit -c '{"function":"getRecordCount","Args":[]}'

echo "=== Testing storeVerdict ==="
peer chaincode invoke \
  -o localhost:7050 \
  --ordererTLSHostnameOverride orderer.example.com \
  --tls \
  --cafile $NW/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem \
  -C mychannel -n idsaudit \
  --peerAddresses localhost:7051 \
  --tlsRootCertFiles $NW/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt \
  --peerAddresses localhost:9051 \
  --tlsRootCertFiles $NW/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
  -c '{"function":"storeVerdict","Args":["ESP32_TEST","D00061FE8CE0","dfc2dcd4","TRUSTED","30.5","45.0","5000","1718000000"]}'

sleep 3

echo "=== Count after insert ==="
peer chaincode query -C mychannel -n idsaudit -c '{"function":"getRecordCount","Args":[]}'

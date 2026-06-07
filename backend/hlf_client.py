"""
Hyperledger Fabric Client for Python
=====================================

Connects to HLF network and submits transactions asynchronously.
"""

import subprocess
import json
import os
import threading
from queue import Queue
from typing import Dict
import time


class HyperledgerFabricClient:
    """
    Async client for Hyperledger Fabric.
    
    Uses peer CLI commands to interact with chaincode.
    Runs in background thread to avoid blocking main application.
    """
    
    def __init__(self, network_path: str, channel: str = "mychannel", chaincode: str = "idsaudit"):
        """
        Initialize HLF client.
        
        Args:
            network_path: Path to fabric-samples/test-network
            channel: Channel name
            chaincode: Chaincode name
        """
        self.network_path = network_path
        self.channel = channel
        self.chaincode = chaincode
        self.queue = Queue()
        self.running = False
        self.transaction_count = 0
        self.success_count = 0
        self.error_count = 0
        
        # Set up environment
        self.env = os.environ.copy()
        self.env.update({
            "FABRIC_CFG_PATH": f"{network_path}/../config/",
            "CORE_PEER_TLS_ENABLED": "true",
            "CORE_PEER_LOCALMSPID": "Org1MSP",
            "CORE_PEER_TLS_ROOTCERT_FILE": f"{network_path}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt",
            "CORE_PEER_MSPCONFIGPATH": f"{network_path}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp",
            "CORE_PEER_ADDRESS": "localhost:7051"
        })
    
    def start(self):
        """Start background worker thread."""
        self.running = True
        worker = threading.Thread(target=self._process_queue, daemon=True)
        worker.start()
        print("✅ Hyperledger Fabric worker started")
    
    def stop(self):
        """Stop background worker."""
        self.running = False
        print("🛑 Hyperledger Fabric worker stopped")
    
    def submit_verdict(self, verdict_data: Dict):
        """
        Submit verdict to blockchain (non-blocking).
        
        Args:
            verdict_data: Detection verdict to store
        """
        self.queue.put(verdict_data)
        print(f"📝 Queued for HLF: {verdict_data.get('device_id')} - {verdict_data.get('verdict')}")
    
    def _process_queue(self):
        """Background worker processes queue."""
        while self.running:
            try:
                if not self.queue.empty():
                    data = self.queue.get()
                    success = self._invoke_chaincode(data)
                    
                    if success:
                        self.success_count += 1
                        print(f"⛓️ HLF TX #{self.transaction_count}: SUCCESS")
                    else:
                        self.error_count += 1
                        print(f"❌ HLF TX #{self.transaction_count}: FAILED")
                    
                    self.transaction_count += 1
                else:
                    time.sleep(1)  # Wait if queue empty
            except Exception as e:
                print(f"❌ HLF worker error: {e}")
                time.sleep(1)
    
    def _invoke_chaincode(self, data: Dict) -> bool:
        """
        Invoke chaincode to store verdict.
        
        Args:
            data: Verdict data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build peer chaincode invoke command
            cmd = [
                "peer", "chaincode", "invoke",
                "-o", "localhost:7050",
                "--ordererTLSHostnameOverride", "orderer.example.com",
                "--tls",
                "--cafile", f"{self.network_path}/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem",
                "-C", self.channel,
                "-n", self.chaincode,
                "--peerAddresses", "localhost:7051",
                "--tlsRootCertFiles", f"{self.network_path}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt",
                "--peerAddresses", "localhost:9051",
                "--tlsRootCertFiles", f"{self.network_path}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt",
                "-c", json.dumps({
                    "function": "storeVerdict",
                    "Args": [
                        str(data.get("device_id", "UNKNOWN")),
                        str(data.get("uid", "UNKNOWN")),
                        str(data.get("firmware", "UNKNOWN")),
                        str(data.get("verdict", "UNKNOWN")),
                        str(data.get("temperature", 0)),
                        str(data.get("humidity", 0)),
                        str(data.get("interval", 0)),
                        str(data.get("timestamp", int(time.time())))
                    ]
                })
            ]
            
            # Execute command
            result = subprocess.run(
                cmd,
                cwd=self.network_path,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Chaincode invoke error: {e}")
            return False
    
    def query_record_count(self) -> int:
        """
        Query total number of records on blockchain.
        
        Returns:
            Record count
        """
        try:
            cmd = [
                "peer", "chaincode", "query",
                "-C", self.channel,
                "-n", self.chaincode,
                "-c", '{"function":"getRecordCount","Args":[]}'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.network_path,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("count", 0)
            
            return 0
            
        except Exception as e:
            print(f"Query error: {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """Get worker statistics."""
        return {
            "total_transactions": self.transaction_count,
            "successful": self.success_count,
            "failed": self.error_count,
            "queue_size": self.queue.qsize(),
            "success_rate": f"{(self.success_count / max(self.transaction_count, 1)) * 100:.1f}%"
        }


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    print("="*70)
    print("🔗 HYPERLEDGER FABRIC CLIENT - DEMO")
    print("="*70)
    
    # Initialize client
    client = HyperledgerFabricClient(
        network_path=os.path.expanduser("~/fabric-iot-ids/fabric-samples/test-network")
    )
    
    # Start worker
    client.start()
    
    # Submit some test verdicts
    print("\n📝 Submitting test verdicts...")
    
    test_verdicts = [
        {"device_id": "ESP32_TEST1", "uid": "UID123", "firmware": "FW_v1", "verdict": "TRUSTED", "temperature": 30.5, "humidity": 45.0, "interval": 5000, "timestamp": int(time.time())},
        {"device_id": "ESP32_TEST2", "uid": "FAKE_UID", "firmware": "FW_v1", "verdict": "CLONE", "temperature": 55.0, "humidity": 10.0, "interval": 3500, "timestamp": int(time.time())},
        {"device_id": "ESP32_TEST1", "uid": "UID123", "firmware": "BAD_FW", "verdict": "TAMPER", "temperature": 30.0, "humidity": 50.0, "interval": 5000, "timestamp": int(time.time())}
    ]
    
    for verdict in test_verdicts:
        client.submit_verdict(verdict)
        time.sleep(0.5)
    
    # Wait for processing
    print("\n⏳ Waiting for transactions to complete...")
    time.sleep(15)
    
    # Show stats
    print("\n📊 Client Statistics:")
    stats = client.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Query blockchain
    print("\n🔍 Querying blockchain record count...")
    count = client.query_record_count()
    print(f"   Total records on blockchain: {count}")
    
    # Stop worker
    client.stop()
    
    print("\n" + "="*70)
    print("✅ Demo complete!")
    print("="*70)
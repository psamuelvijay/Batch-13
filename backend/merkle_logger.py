"""
Tamper-Proof Logging System using Merkle Tree and SHA-256
==========================================================

This module provides blockchain-inspired immutable logging without
the overhead of a distributed blockchain.

Features:
- SHA-256 cryptographic hashing
- Chain-linked entries (like blockchain blocks)
- Merkle tree verification
- Tamper detection
- Fast (< 1ms per entry)
- Zero external dependencies
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class MerkleTreeLogger:
    """
    Implements a tamper-proof logging system using:
    1. SHA-256 hashing for integrity
    2. Chain linking (each entry references previous hash)
    3. Merkle tree for batch verification
    """
    
    def __init__(self, secret_key: str = ""):
        """
        Initialize the logger.
        
        Args:
            secret_key: Secret key for HMAC-style signing (optional but recommended)
        """
        self.secret_key = secret_key
        self.previous_hash = "0" * 64  # Genesis hash (64 char hex)
        self.entry_count = 0
        
    def _compute_hash(self, data: str) -> str:
        """
        Compute SHA-256 hash of data + secret key.
        
        Args:
            data: String to hash
            
        Returns:
            64-character hexadecimal hash
        """
        combined = data + self.secret_key
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def create_signed_entry(self, verdict_data: Dict) -> Dict:
        """
        Create a cryptographically signed log entry.
        
        This works like a blockchain block:
        1. Takes the data + previous hash
        2. Computes new hash
        3. Links to previous entry
        
        Args:
            verdict_data: Dictionary containing detection verdict info
            
        Returns:
            Signed entry with hash and previous_hash
        """
        # Create entry structure
        entry = {
            "entry_id": self.entry_count,
            "timestamp": int(time.time()),
            "timestamp_iso": datetime.utcnow().isoformat(),
            "data": verdict_data,
            "previous_hash": self.previous_hash
        }
        
        # Compute hash of this entry
        entry_str = json.dumps(entry, sort_keys=True)
        current_hash = self._compute_hash(entry_str)
        
        # Add hash to entry
        entry["hash"] = current_hash
        
        # Update state for next entry
        self.previous_hash = current_hash
        self.entry_count += 1
        
        return entry
    
    def verify_entry(self, entry: Dict) -> Tuple[bool, str]:
        """
        Verify that an entry hasn't been tampered with.
        
        Args:
            entry: Entry to verify
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Extract claimed hash
        claimed_hash = entry.get("hash")
        if not claimed_hash:
            return False, "Entry missing hash field"
        
        # Recompute hash
        temp_entry = entry.copy()
        temp_entry.pop("hash")
        entry_str = json.dumps(temp_entry, sort_keys=True)
        computed_hash = self._compute_hash(entry_str)
        
        # Compare
        if computed_hash != claimed_hash:
            return False, f"Hash mismatch: computed {computed_hash[:8]}... != claimed {claimed_hash[:8]}..."
        
        return True, "Entry is valid"
    
    def verify_chain(self, entries: List[Dict]) -> Tuple[bool, str]:
        """
        Verify an entire chain of entries.
        
        This checks:
        1. Each entry's hash is correct
        2. Each entry links to the previous entry
        
        Args:
            entries: List of entries in chronological order
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not entries:
            return True, "Empty chain (valid)"
        
        prev_hash = "0" * 64  # Genesis
        
        for i, entry in enumerate(entries):
            # Verify hash
            is_valid, msg = self.verify_entry(entry)
            if not is_valid:
                return False, f"Entry {i} (ID {entry.get('entry_id')}): {msg}"
            
            # Verify chain link
            if entry.get("previous_hash") != prev_hash:
                return False, f"Chain broken at entry {i}: previous_hash mismatch"
            
            prev_hash = entry["hash"]
        
        return True, "All entries valid and properly chained"
    
    def build_merkle_tree(self, entries: List[Dict]) -> str:
        """
        Build a Merkle tree root hash from entries.
        
        This creates a cryptographic commitment to all entries
        that can be verified efficiently.
        
        Args:
            entries: List of log entries
            
        Returns:
            Merkle root hash
        """
        if not entries:
            return "0" * 64
        
        # Get hashes from all entries
        hashes = [entry["hash"] for entry in entries]
        
        # Build tree bottom-up
        while len(hashes) > 1:
            next_level = []
            
            # Pair up hashes
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    # Hash the pair
                    combined = hashes[i] + hashes[i + 1]
                    parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                    next_level.append(parent_hash)
                else:
                    # Odd one out, promote it
                    next_level.append(hashes[i])
            
            hashes = next_level
        
        return hashes[0]
    
    def get_statistics(self, entries: List[Dict]) -> Dict:
        """
        Get statistics about the log chain.
        
        Args:
            entries: List of entries
            
        Returns:
            Dictionary of statistics
        """
        if not entries:
            return {
                "total_entries": 0,
                "merkle_root": "0" * 64,
                "chain_valid": True
            }
        
        is_valid, msg = self.verify_chain(entries)
        merkle_root = self.build_merkle_tree(entries)
        
        # Analyze verdicts
        verdicts = {}
        for entry in entries:
            verdict = entry["data"].get("verdict", "UNKNOWN")
            verdicts[verdict] = verdicts.get(verdict, 0) + 1
        
        return {
            "total_entries": len(entries),
            "first_entry": entries[0]["timestamp_iso"] if entries else None,
            "last_entry": entries[-1]["timestamp_iso"] if entries else None,
            "merkle_root": merkle_root,
            "chain_valid": is_valid,
            "chain_message": msg,
            "verdict_breakdown": verdicts
        }


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    print("="*70)
    print("🔐 TAMPER-PROOF LOGGING SYSTEM - DEMO")
    print("="*70)
    
    # Initialize logger
    logger = MerkleTreeLogger(secret_key="your-secret-key-here")
    
    # Create some test entries
    print("\n📝 Creating test log entries...")
    
    entries = []
    
    test_data = [
        {"device_id": "ESP32_01", "verdict": "TRUSTED", "confidence": 0.98},
        {"device_id": "ESP32_01", "verdict": "TRUSTED", "confidence": 0.97},
        {"device_id": "ESP32_02", "verdict": "CLONE", "confidence": 0.95},
        {"device_id": "ESP32_01", "verdict": "ANOMALY", "confidence": 0.89},
        {"device_id": "ESP32_02", "verdict": "CLONE|TAMPER", "confidence": 0.99}
    ]
    
    for data in test_data:
        entry = logger.create_signed_entry(data)
        entries.append(entry)
        print(f"✅ Entry {entry['entry_id']}: {data['verdict']}")
        time.sleep(0.1)  # Small delay for different timestamps
    
    # Verify chain
    print("\n🔍 Verifying chain integrity...")
    is_valid, msg = logger.verify_chain(entries)
    print(f"{'✅' if is_valid else '❌'} {msg}")
    
    # Show statistics
    print("\n📊 Chain Statistics:")
    stats = logger.get_statistics(entries)
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Demonstrate tamper detection
    print("\n🔧 Testing tamper detection...")
    print("   Modifying entry #2...")
    entries[2]["data"]["verdict"] = "TAMPERED_DATA"
    
    is_valid, msg = logger.verify_chain(entries)
    print(f"{'✅' if is_valid else '❌'} {msg}")
    
    if not is_valid:
        print("   🎉 Tampering detected successfully!")
    
    print("\n" + "="*70)
    print("✅ Demo complete!")
    print("="*70)
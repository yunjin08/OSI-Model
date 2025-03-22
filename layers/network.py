
# File: osi_model/layers/network.py
import struct
from osi_model.layers.layer import Layer 

class NetworkLayer(Layer):
    """Layer 3: Network Layer
    Handles IP addressing and packet routing."""
    
    def __init__(self, src_ip, dst_ip):
        super().__init__()
        self.src_ip = src_ip  # 4-byte IP address
        self.dst_ip = dst_ip  # 4-byte IP address
        self.ttl = 64  # Time To Live

    def process_outgoing(self, data):
        """Create IP packet with header"""
        # IP header: version(4) + IHL(4) + TTL(8) + src_ip(32) + dst_ip(32)
        version_ihl = struct.pack('!B', (4 << 4) | 5)  # IPv4, IHL=5
        ttl = struct.pack('!B', self.ttl)
        # Correct order: src_ip, then dst_ip
        header = version_ihl + ttl + self.src_ip + self.dst_ip
        return header + data

    def process_incoming(self, data):
        """Process incoming IP packet"""
        if len(data) < 10:  # Minimum header size
            print("IP packet too small")
            return b''
            
        # Extract and verify header
        version_ihl = data[0]
        version = version_ihl >> 4
        if version != 4:  # Check IPv4
            print("Invalid IP version")
            return b''
            
        # Extract IP addresses in correct order
        src_ip = data[2:6]  # Source IP comes first after TTL
        dst_ip = data[6:10]  # Destination IP comes second
        
        # Debug print with correct byte order
        print(f"Network packet received:")
        print(f"  - Version: IPv{version}")
        print(f"  - Source IP: {'.'.join(str(b) for b in src_ip)}")
        print(f"  - Destination IP: {'.'.join(str(b) for b in dst_ip)}")
        
        # Verify destination IP matches our IP
        if dst_ip != self.src_ip:
            print(f"IP address mismatch:")
            print(f"  - Received: {'.'.join(str(b) for b in dst_ip)}")
            print(f"  - Expected: {'.'.join(str(b) for b in self.src_ip)}")
            return b''
            
        return data[10:]  # Return payload after header

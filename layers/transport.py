# File: osi_model/layers/transport.py
import struct
import zlib
from osi_model.layers.layer import Layer 

class TransportLayer(Layer):
    """Layer 4: Transport Layer
    Implements reliable data transfer with sequencing and error checking."""
    
    def __init__(self):
        super().__init__()
        self.seq = 0
        self.expected_seq = 1
        self.window_size = 8

    def process_outgoing(self, data):
        """Add transport header with sequence number and checksum"""
        self.seq = (self.seq + 1) % 65536
        seq_bytes = struct.pack('!H', self.seq)
        window = struct.pack('!H', self.window_size)
        checksum = struct.pack('!I', self._calculate_checksum(seq_bytes + window + data))
        return seq_bytes + window + checksum + data

    def process_incoming(self, data):
        """Process incoming segment and verify sequence and checksum"""
        if len(data) < 8:
            return b''
            
        # Extract header fields
        seq = struct.unpack('!H', data[:2])[0]
        window = struct.unpack('!H', data[2:4])[0]
        checksum = data[4:8]
        payload = data[8:]
        
        # Verify checksum
        if self._calculate_checksum(data[:4] + payload) != struct.unpack('!I', checksum)[0]:
            print("Transport checksum failed")
            return b''
            
        # Verify sequence number
        if seq != self.expected_seq:
            print(f"Unexpected sequence number: {seq}, expected: {self.expected_seq}")
            return b''
            
        self.expected_seq = (self.expected_seq + 1) % 65536
        return payload

    def _calculate_checksum(self, data):
        """Calculate checksum for error detection"""
        return zlib.adler32(data) & 0xFFFFFFFF

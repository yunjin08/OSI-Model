# File: osi_model/layers/datalink.py
import struct
import zlib
from osi_model.layers.layer import Layer 

class DataLinkLayer(Layer):
    """Layer 2: Data Link Layer
    Handles MAC addressing and frame creation."""
    
    def __init__(self, src_mac, dst_mac):
        super().__init__()
        if len(src_mac) != 6 or len(dst_mac) != 6:
            raise ValueError("MAC addresses must be exactly 6 bytes")
        self.src_mac = src_mac  # 6-byte MAC address
        self.dst_mac = dst_mac  # 6-byte MAC address

    def process_outgoing(self, data):
        """Create a frame with MAC addresses and FCS"""
        if not isinstance(data, bytes):
            try:
                data = data.encode('utf-8')
            except AttributeError:
                print("Warning: Data is not bytes or string, attempting to convert")
                data = str(data).encode('utf-8')
                
        # Add MAC addresses (12 bytes total)
        header = self.src_mac + self.dst_mac
        # Add Frame Check Sequence (4 bytes)
        fcs = struct.pack('!I', self._calculate_fcs(header + data))
        frame = header + data + fcs
        
        # Debug print the frame contents
        print(f"DataLink frame created: size={len(frame)}")
        print(f"  - Source MAC: {self.src_mac.hex(':')}")
        print(f"  - Dest MAC: {self.dst_mac.hex(':')}")
        print(f"  - FCS: 0x{fcs.hex()}")
        return frame

    def process_incoming(self, data):
        """Process incoming frame and verify FCS"""
        if not isinstance(data, (bytes, bytearray)):
            print(f"Warning: Received non-bytes data in DataLink: {type(data)}")
            return b''
            
        if len(data) < 16:  # 12 bytes header + 4 bytes FCS minimum
            print(f"Frame too small for DataLink: {len(data)} bytes")
            return b''
        
        try:
            # Extract frame components
            src_mac = data[:6]
            dst_mac = data[6:12]
            payload = data[12:-4]
            fcs = data[-4:]
            
            # Debug print the frame components
            print(f"DataLink frame received:")
            print(f"  - Source MAC: {src_mac.hex(':')}")
            print(f"  - Dest MAC: {dst_mac.hex(':')}")
            print(f"  - Payload size: {len(payload)}")
            print(f"  - FCS: 0x{fcs.hex()}")
            
            # Verify destination MAC - compare with our MAC address
            if dst_mac != self.src_mac:  # Changed from self.dst_mac to self.src_mac
                print(f"MAC address mismatch:")
                print(f"  - Received: {dst_mac.hex(':')}")
                print(f"  - Expected: {self.src_mac.hex(':')}")
                return b''
                
            # Verify FCS
            calculated_fcs = self._calculate_fcs(data[:-4])
            received_fcs = struct.unpack('!I', fcs)[0]
            if calculated_fcs != received_fcs:
                print(f"FCS check failed:")
                print(f"  - Calculated: 0x{calculated_fcs:08x}")
                print(f"  - Received: 0x{received_fcs:08x}")
                return b''
                
            print(f"DataLink frame verified successfully")
            return payload
            
        except struct.error as e:
            print(f"Error unpacking DataLink frame: {e}")
            return b''

    def _calculate_fcs(self, data):
        """Calculate Frame Check Sequence"""
        return zlib.crc32(data) & 0xFFFFFFFF

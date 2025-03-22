
# File: osi_model/layers/session.py
import struct
from osi_model.layers.layer import Layer 

class SessionLayer(Layer):
    """Layer 5: Session Layer
    Manages session establishment, maintenance, and termination."""
    
    def __init__(self, session_id):
        super().__init__()
        self.session_id = session_id
        self.is_active = False
        self.sequence = 0

    def process_outgoing(self, data):
        """Add session control information"""
        self.sequence += 1
        header = struct.pack('!IQ', self.session_id, self.sequence)
        return header + data

    def process_incoming(self, data):
        """Process session information"""
        if len(data) < 12:  # 4 bytes session_id + 8 bytes sequence
            return b''
            
        session_id, sequence = struct.unpack('!IQ', data[:12])
        if session_id != self.session_id:
            print("Invalid session ID")
            return b''
            
        return data[12:]

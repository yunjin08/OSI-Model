
# File: osi_model/layers/presentation.py
import zlib
from osi_model.layers.layer import Layer 

class PresentationLayer(Layer):
    """Layer 6: Presentation Layer
    Handles data encryption, compression, and format conversion."""
    
    def __init__(self, key):
        super().__init__()
        self.key = key

    def process_outgoing(self, data):
        """Compress and encrypt data"""
        # First compress
        compressed = zlib.compress(data)
        # Then encrypt (simple XOR encryption for demonstration)
        encrypted = bytes([b ^ self.key[i % len(self.key)] 
                         for i, b in enumerate(compressed)])
        return encrypted

    def process_incoming(self, data):
        """Decrypt and decompress data"""
        # First decrypt
        decrypted = bytes([b ^ self.key[i % len(self.key)] 
                         for i, b in enumerate(data)])
        # Then decompress
        try:
            decompressed = zlib.decompress(decrypted)
            return decompressed
        except zlib.error as e:
            print("Decompression failed:", e)
            return b''

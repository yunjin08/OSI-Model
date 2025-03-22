
# File: osi_model/layers/application.py
from osi_model.layers.layer import Layer 

class ApplicationLayer(Layer):
    """Layer 7: Application Layer
    Implements application protocol (HTTP-like in this case)."""
    
    def __init__(self):
        super().__init__()
        self.received_data = None

    def process_outgoing(self, data):
        """Format data as HTTP-like request/response"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return data

    def process_incoming(self, data):
        """Process HTTP-like request/response"""
        try:
            self.received_data = data.decode('utf-8')
            print("Application Layer received:", self.received_data)
            return self.received_data
        except UnicodeDecodeError:
            print("Failed to decode application data")
            return None

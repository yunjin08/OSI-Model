class Layer:
    """Base class for all OSI layers"""
    def __init__(self):
        self.upper_layer = None
        self.lower_layer = None

    def send_down(self, data):
        """Send data down to the next layer"""
        print(f"\n{self.__class__.__name__} sending down:", data[:50], "..." if len(str(data)) > 50 else "")
        processed_data = self.process_outgoing(data)
        if self.lower_layer:
            self.lower_layer.send_down(processed_data)

    def receive_up(self, data):
        """Receive data from the lower layer and pass it up"""
        print(f"\n{self.__class__.__name__} received:", data[:50], "..." if len(str(data)) > 50 else "")
        if data is None or data == b'':
            print(f"{self.__class__.__name__} received empty data, stopping propagation")
            return

 
        if self.upper_layer:
            self.upper_layer.receive_up(data)
        return


        # For all other layers, process the incoming data
        try:
            # Process the data through this layer
            print('processing')
            processed_data = self.process_incoming(data)
            
            # If processing failed, stop propagation
            if processed_data is None or processed_data == b'':
                print(f"{self.__class__.__name__} processing failed, stopping propagation")
                return
                
            # Pass the processed data up to the next layer
            if self.upper_layer:
                print(f"{self.__class__.__name__} passing processed data up")
                self.upper_layer.receive_up(processed_data)
                
        except Exception as e:
            print(f"Error in {self.__class__.__name__} processing: {e}")
            return

    def process_outgoing(self, data):
        raise NotImplementedError

    def process_incoming(self, data):
        raise NotImplementedError


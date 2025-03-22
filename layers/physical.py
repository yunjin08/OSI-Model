# File: osi_model/layers/physical.py
import socket
import struct
import time
from threading import Thread, Event
from osi_model.layers.layer import Layer 

class PhysicalLayer(Layer):
    """Layer 1: Physical Layer
    Handles the actual transmission of raw bits over the network medium.
    In this simulation, we use TCP sockets to simulate the physical transmission."""
    
    PREAMBLE = b'\xAA'  # 10101010 in binary
    
    def __init__(self, host, port, is_server=False):
        super().__init__()
        self.host = host
        self.port = port
        self.is_server = is_server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Add timeout to prevent infinite waiting
        self.socket.settimeout(30) 
        self.conn = None
        self.running = Event()
        self.listen_thread = None

    def start(self):
        """Start the physical layer connection"""
        print(f"{self.__class__.__name__} starting")
        self.running.set()
        
        try:
            if self.is_server:
                try:
                    self.socket.bind((self.host, self.port))
                    self.socket.listen(1)
                    print(f"{self.__class__.__name__} is listening on {self.host}:{self.port}")
                    # Set a timeout for accept()
                    self.socket.settimeout(30)  # Increased timeout to 30 seconds
                    self.conn, addr = self.socket.accept()
                    print(f"{self.__class__.__name__} accepted connection from {addr}")
                    # Reset timeout for normal operation
                    self.conn.settimeout(None)
                except socket.timeout:
                    print("Timeout waiting for client connection")
                    self.cleanup()
                    raise
                except Exception as e:
                    print(f"Error in server setup: {e}")
                    self.cleanup()
                    raise
            else:
                max_retries = 5
                retry_delay = 1
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        print(f"{self.__class__.__name__} is client, connecting to {self.host}:{self.port} (attempt {attempt + 1})")
                        self.socket.connect((self.host, self.port))
                        print(f"{self.__class__.__name__} connected to server")
                        # Reset timeout for normal operation
                        self.socket.settimeout(None)
                        break
                    except (ConnectionRefusedError, socket.timeout) as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            print(f"Connection attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            # Create a new socket for the next attempt
                            self.socket.close()
                            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            self.socket.settimeout(30)
                        else:
                            print(f"All connection attempts failed")
                            raise last_error

            self.listen_thread = Thread(target=self.listen, daemon=True)
            self.listen_thread.start()
            
        except Exception as e:
            print(f"Failed to start {self.__class__.__name__}: {e}")
            self.cleanup()
            raise

    def cleanup(self):
        """Clean up resources"""
        self.running.clear()
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        try:
            self.socket.close()
        except:
            pass

    def listen(self):
        """Listen for incoming data"""
        conn = self.conn if self.is_server else self.socket
        buffer = bytearray()
        
        while self.running.is_set():
            try:
                # Read data in chunks
                chunk = conn.recv(1024)
                if not chunk:
                    print("Connection closed")
                    break
                
                print(f"Received chunk: {chunk[:20]!r}...")
                buffer.extend(chunk)
                
                # Process complete frames
                while len(buffer) >= 3:  # Minimum frame size (preamble + length)
                    # Look for preamble
                    preamble_pos = buffer.find(self.PREAMBLE)
                    if preamble_pos == -1:
                        # No preamble found, clear buffer and wait for more data
                        print("No preamble found in buffer, clearing")
                        buffer.clear()
                        break
                    
                    # Remove data before preamble if any
                    if preamble_pos > 0:
                        print(f"Discarding {preamble_pos} bytes before preamble")
                        buffer = buffer[preamble_pos:]
                    
                    # Check if we have enough data to read the length
                    if len(buffer) < 3:
                        print("Buffer too small to read length, waiting for more data")
                        break
                    
                    # Extract frame length
                    frame_length = struct.unpack('!H', buffer[1:3])[0]
                    total_length = frame_length + 3  # preamble + length + data
                    
                    print(f"Found frame: preamble at 0, length={frame_length}, need={total_length} bytes")
                    
                    # Check if we have the complete frame
                    if len(buffer) < total_length:
                        print(f"Incomplete frame: have {len(buffer)}, need {total_length} bytes")
                        break
                    
                    # Extract the complete frame
                    frame = bytes(buffer[:total_length])  # Convert to bytes for consistency
                    
                    # Process the frame
                    processed_data = self.process_incoming(frame)
                    if processed_data:
                        # This will call our overridden method
                        self.receive_up(processed_data)

                    # Remove the processed frame from buffer
                    buffer = buffer[total_length:]
                    print(f"Removed frame from buffer, {len(buffer)} bytes remaining")
                    
            except Exception as e:
                if self.running.is_set():
                    print(f"Error in listening: {e}")
                break
        
        self.cleanup()

    def send_down(self, data):
        """Send data over the physical medium"""
        try:
            if not self.running.is_set():
                raise Exception("Connection is closed")
            
            # Process the data into a frame
            frame = self.process_outgoing(data)
            
            # Debug print the frame contents
            print(f"Sending frame:")
            print(f"  - Total size: {len(frame)}")
            print(f"  - First 20 bytes: {frame[:20]!r}")
            
            # Send the frame in a single call to prevent fragmentation
            if self.is_server:
                print(f"{self.__class__.__name__} sending data to client")
                self.conn.sendall(frame)
            else:
                print(f"{self.__class__.__name__} sending data to server")
                self.socket.sendall(frame)
                
        except Exception as e:
            print(f"Error sending data: {e}")
            self.cleanup()
            raise

    def process_outgoing(self, data):
        """Convert data to physical bits with frame synchronization"""
        if not isinstance(data, bytes):
            try:
                data = data.encode('utf-8')
            except AttributeError:
                print("Warning: Data is not bytes or string, attempting to convert")
                data = str(data).encode('utf-8')
            
        # Calculate frame length (excluding preamble and length field)
        length = len(data)
        length_bytes = struct.pack('!H', length)  # 2 bytes for length
        
        # Construct the frame: preamble + length + data
        frame = self.PREAMBLE + length_bytes + data
        
        # Debug print frame details
        print(f"Physical frame created:")
        print(f"  - Preamble: 0x{self.PREAMBLE.hex()}")
        print(f"  - Length: {length} (0x{length_bytes.hex()})")
        print(f"  - Total size: {len(frame)}")
        print(f"  - First 20 bytes: {frame[:20]!r}")
        
        return frame

    def process_incoming(self, data):
        """Process incoming physical bits and check frame synchronization"""
        if not isinstance(data, (bytes, bytearray)):
            print(f"Warning: Received non-bytes data: {type(data)}")
            return None
            
        # Debug print the received data
        print(f"Processing physical frame:")  # Updated debug message
        print(f"  - Total size: {len(data)}")
        print(f"  - First 20 bytes: {data[:20]!r}")
            
        if len(data) < 3:  # Minimum frame size (1 byte preamble + 2 bytes length)
            print("Frame too small: minimum 3 bytes required")
            return None
            
        # Check preamble
        if data[0:1] != self.PREAMBLE:
            print(f"Invalid preamble: got 0x{data[0:1].hex()}, expected 0x{self.PREAMBLE.hex()}")
            return None
            
        # Extract frame length
        length = struct.unpack('!H', data[1:3])[0]
        print(f"Frame length from header: {length}")
        
        # Check if we have the complete frame
        if len(data) < length + 3:  # preamble + length + data
            print(f"Incomplete frame: got {len(data)}, need {length + 3}")
            return None
            
        # Extract and return the payload
        payload = data[3:3+length]  # Only extract the specified length
        print(f"Extracted physical payload: size={len(payload)}, first 20 bytes={payload[:20]!r}")
        return payload

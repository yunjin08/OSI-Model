import socket
import struct
import zlib
import time
from threading import Thread, Event
import signal
import sys

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
        
        # Special handling for Physical layer since it already processed in listen()
        if isinstance(self, PhysicalLayer):
            if self.upper_layer:
                self.upper_layer.receive_up(data)
            return
            
        # For all other layers, process the incoming data
        try:
            # Process the data through this layer
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
        header = version_ihl + ttl + self.src_ip + self.dst_ip
        return header + data

    def process_incoming(self, data):
        """Process incoming IP packet"""
        if len(data) < 7:  # Minimum header size
            return b''
            
        # Extract and verify header
        version_ihl = data[0]
        version = version_ihl >> 4
        if version != 4:  # Check IPv4
            print("Invalid IP version")
            return b''
        
        return data[10:]  # Adjust based on header length

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

def create_server():
    """Create and configure server-side layers"""
    physical = PhysicalLayer('localhost', 12345, is_server=True)
    # Fix MAC addresses to use proper hex values
    datalink = DataLinkLayer(b'\x11\x22\x33\x44\x55\x66', b'\x77\x88\x99\xaa\xbb\xcc')
    network = NetworkLayer(b'\x0a\x00\x00\x01', b'\x0a\x00\x00\x02')
    transport = TransportLayer()
    session = SessionLayer(1234)
    presentation = PresentationLayer(b'secret')
    application = ApplicationLayer()

    # Link the layers
    physical.upper_layer = datalink
    datalink.lower_layer = physical
    datalink.upper_layer = network
    network.lower_layer = datalink
    network.upper_layer = transport
    transport.lower_layer = network
    transport.upper_layer = session
    session.lower_layer = transport
    session.upper_layer = presentation
    presentation.lower_layer = session
    presentation.upper_layer = application
    application.lower_layer = presentation

    return physical, application

def create_client():
    """Create and configure client-side layers"""
    physical = PhysicalLayer('localhost', 12345, is_server=False)
    # Fix MAC addresses to use proper hex values (reversed from server)
    datalink = DataLinkLayer(b'\x77\x88\x99\xaa\xbb\xcc', b'\x11\x22\x33\x44\x55\x66')
    network = NetworkLayer(b'\x0a\x00\x00\x02', b'\x0a\x00\x00\x01')
    transport = TransportLayer()
    session = SessionLayer(1234)
    presentation = PresentationLayer(b'secret')
    application = ApplicationLayer()

    # Link the layers
    physical.upper_layer = datalink
    datalink.lower_layer = physical
    datalink.upper_layer = network
    network.lower_layer = datalink
    network.upper_layer = transport
    transport.lower_layer = network
    transport.upper_layer = session
    session.lower_layer = transport
    session.upper_layer = presentation
    presentation.lower_layer = session
    presentation.upper_layer = application
    application.lower_layer = presentation

    return physical, application

def main():
    """Main function to demonstrate the OSI model implementation"""
    server = None
    client = None
    
    def signal_handler(signum, frame):
        print("\nCleaning up...")
        if server:
            server.cleanup()
        if client:
            client.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Create and start server
        print("\n=== Starting Server ===")
        server, server_app = create_server()
        
        # Start server in a separate thread
        server_thread = Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        # Give the server time to start up
        time.sleep(1)

        # Create and start client
        print("\n=== Starting Client ===")
        client, client_app = create_client()
        
        try:
            client.start()
        except Exception as e:
            print(f"Client failed to start: {e}")
            if server:
                server.cleanup()
            sys.exit(1)

        # Wait for connection establishment
        time.sleep(1)

        # Send HTTP-like request from client to server
        print("\n=== Sending Request ===")
        request = """
GET /index.html HTTP/1.1
Host: localhost:12345
User-Agent: OSI-Model-Client/1.0
Accept: text/html

Hello, Server! This is a test message.
"""
        try:
            print("\n=== Data Flow: Application → Physical ===")
            client_app.send_down(request)
            print("\nRequest sent successfully")
            
            # Wait a bit for the response to propagate through layers
            time.sleep(0.5)
            print("\n=== Data Flow Complete ===")
            
        except Exception as e:
            print(f"Failed to send request: {e}")
            raise

        # Keep the main thread running
        print("\n=== Server Running (Press Ctrl+C to exit) ===")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        print("\nCleaning up connections...")
        if server:
            server.cleanup()
        if client:
            client.cleanup()

if __name__ == "__main__":
    main()
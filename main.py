# File: osi_model/main.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import signal
import sys
from threading import Thread
from utils import initialize_addresses
import osi_model.config as config
from osi_model.layers import (
    PhysicalLayer, DataLinkLayer, NetworkLayer, TransportLayer, 
    SessionLayer, PresentationLayer, ApplicationLayer
)

def create_server():
    """Create and configure server-side layers"""
    physical = PhysicalLayer('localhost', 12345, is_server=True)
    
    datalink = DataLinkLayer(config.SERVER_MAC, config.CLIENT_MAC)
    network = NetworkLayer(config.SERVER_IP, config.CLIENT_IP)
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

    print("\nClient Configuration:")
    print(f"MAC Address: {':'.join(f'{b:02x}' for b in config.CLIENT_MAC)}")
    print(f"IP Address: {'.'.join(str(b) for b in config.CLIENT_IP)}")

    datalink = DataLinkLayer(config.CLIENT_MAC, config.SERVER_MAC)
    network = NetworkLayer(config.CLIENT_IP, config.SERVER_IP)
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
        # Get real network addresses
        initialize_addresses()
        print("\n=== Starting Server ===")
        print("\n=== Debugging Network Addresses ===")
        print(f"config.SERVER_MAC: {config.SERVER_MAC}")
        print(f"config.CLIENT_MAC: {config.CLIENT_MAC}")
        print(f"config.SERVER_IP: {config.SERVER_IP}")
        print(f"config.CLIENT_IP: {config.CLIENT_IP}")
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

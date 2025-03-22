# File: osi_model/utils.py
import uuid
import socket
import osi_model.config as config


def get_local_mac_address():
    mac_int = uuid.getnode()
    # Convert MAC from integer to bytes (6 bytes for MAC address)
    mac_bytes = mac_int.to_bytes(6, byteorder='big')
    return mac_bytes

def get_local_ip_address():
    """Get IP address without using netifaces"""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No need for the connection to succeed, just to determine IP
        s.connect(("8.8.8.8", 80))
        ip_addr = s.getsockname()[0]
        s.close()
        # Convert from string format to bytes
        ip_bytes = bytes([int(x) for x in ip_addr.split('.')])
        return ip_bytes
    except Exception:
        print("Warning: Could not determine local IP address, using default")
        # Fallback to a private IP address
        return bytes([192, 168, 0, 1])

def initialize_addresses():
    """Initialize global MAC and IP addresses with real device information"""
    
    # Get real MAC and IP addresses
    local_mac = get_local_mac_address()
    local_ip = get_local_ip_address()
    
    # For server
    config.SERVER_MAC = local_mac
    config.SERVER_IP = local_ip
    
    # For client (in a real setup, these would be different)
    # Here we're simulating a client with modified addresses based on real ones
    config.CLIENT_MAC = bytes([local_mac[0] | 0x02]) + local_mac[1:]  # Modified MAC
    
    # Generate a different but valid IP in the same subnet
    subnet_mask = 24  # Assuming a /24 subnet
    subnet_prefix = local_ip[:3]  # First 3 bytes for /24 subnet
    client_host = (local_ip[3] % 254) + 1  # Ensure it's different from server
    if client_host == local_ip[3]:  # Avoid duplicate IP
        client_host = (client_host % 254) + 1
    config.CLIENT_IP = subnet_prefix + bytes([client_host])
    
    print("\nReal Device Network Information:")
    print(f"Server MAC: {':'.join(f'{b:02x}' for b in config.SERVER_MAC)}")
    print(f"Server IP: {'.'.join(str(b) for b in config.SERVER_IP)}")
    print(f"Client MAC (derived): {':'.join(f'{b:02x}' for b in config.CLIENT_MAC)}")
    print(f"Client IP (derived): {'.'.join(str(b) for b in config.CLIENT_IP)}")


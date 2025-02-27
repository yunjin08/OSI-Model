import socket
import struct
import zlib
from threading import Thread

class Layer:
    def __init__(self):
        self.upper_layer = None
        self.lower_layer = None

    def send_down(self, data):
        processed_data = self.process_outgoing(data)
        if self.lower_layer:
            self.lower_layer.send_down(processed_data)

    def receive_up(self, data):
        processed_data = self.process_incoming(data)
        if self.upper_layer:
            self.upper_layer.receive_up(processed_data)

    def process_outgoing(self, data):
        raise NotImplementedError

    def process_incoming(self, data):
        raise NotImplementedError

class PhysicalLayer(Layer):
    def __init__(self, host, port, is_server=False):
        super().__init__()
        self.host = host
        self.port = port
        self.is_server = is_server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = None

    def start(self):
        if self.is_server:
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.conn, _ = self.socket.accept()
        else:
            self.socket.connect((self.host, self.port))
        Thread(target=self.listen, daemon=True).start()

    def listen(self):
        conn = self.conn if self.is_server else self.socket
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    print("Connection closed")
                    break
                processed_data = self.process_incoming(data)
                self.receive_up(processed_data)
            except Exception as e:
                print("Error in listening: ", e)
                break

    def process_outgoing(self, data):
        bits = ''.join(format(byte, '08b') for byte in data)
        preamble = '10101010'
        bits = preamble + bits
        padding = (8 - (len(bits) % 8)) % 8
        bits += '0' * padding
        bytes_data = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
        return bytes_data

    def process_incoming(self, data):
        bits = ''.join(format(byte, '08b') for byte in data)
        preamble = bits[:8]
        if preamble != '10101010':
            return b''
        data_bits = bits[8:]
        bytes_data = bytes(int(data_bits[i:i+8], 2) for i in range(0, len(data_bits), 8))
        return bytes_data

class DataLinkLayer(Layer):
    def __init__(self, src_mac, dst_mac):
        super().__init__()
        self.src_mac = src_mac
        self.dst_mac = dst_mac

    def process_outgoing(self, data):
        header = struct.pack('!6s6s', self.src_mac, self.dst_mac)
        fcs = struct.pack('!I', self._calculate_fcs(header + data))
        return header + data + fcs

    def process_incoming(self, data):
        if len(data) < 14 + 4:
            return b''
        header, payload, fcs = data[:12], data[12:-4], data[-4:]
        if struct.unpack('!6s', header[6:12])[0] != self.dst_mac:
            return b''
        if self._calculate_fcs(data[:-4]) != struct.unpack('!I', fcs)[0]:
            return b''
        return payload

    def _calculate_fcs(self, data):
        return sum(data) % (1 << 32)

class NetworkLayer(Layer):
    def __init__(self, src_ip, dst_ip):
        super().__init__()
        self.src_ip = src_ip
        self.dst_ip = dst_ip

    def process_outgoing(self, data):
        return struct.pack('!4s4s', self.src_ip, self.dst_ip) + data

    def process_incoming(self, data):
        if len(data) < 8 or struct.unpack('!4s', data[4:8])[0] != self.dst_ip:
            return b''
        return data[8:]

class TransportLayer(Layer):
    def __init__(self):
        super().__init__()
        self.seq = 0

    def process_outgoing(self, data):
        self.seq += 1
        seq_bytes = struct.pack('!I', self.seq)
        checksum = self._calculate_checksum(seq_bytes + data)
        return seq_bytes + checksum + data

    def process_incoming(self, data):
        if len(data) < 8:
            return b''
        seq = struct.unpack('!I', data[:4])[0]
        checksum = struct.unpack('!4s', data[4:8])[0]
        payload = data[8:]
        if self._calculate_checksum(data[:4] + payload) != checksum:
            return b''
        return payload

    def _calculate_checksum(self, data):
        return sum(data) % (1 << 32)

class SessionLayer(Layer):
    def __init__(self, session_id):
        super().__init__()
        self.session_id = session_id

    def process_outgoing(self, data):
        return struct.pack('!I', self.session_id) + data

    def process_incoming(self, data):
        if len(data) < 4 or struct.unpack('!I', data[:4])[0] != self.session_id:
            return b''
        return data[4:]

class PresentationLayer(Layer):
    def __init__(self, key):
        super().__init__()
        self.key = key

    def process_outgoing(self, data):
        compressed = zlib.compress(data)
        return bytes([b ^ self.key[i % len(self.key)] for i, b in enumerate(compressed)])

    def process_incoming(self, data):
        decrypted = bytes([b ^ self.key[i % len(self.key)] for i, b in enumerate(data)])
        return zlib.decompress(decrypted)

class ApplicationLayer(Layer):
    def __init__(self):
        super().__init__()
        self.received_data = None

    def process_outgoing(self, data):
        return data.encode('utf-8')

    def process_incoming(self, data):
        self.received_data = data.decode('utf-8')
        print("Received data:", self.received_data)
        return data.decode('utf-8')

def main():
    # Server setup
    print("Server setup")
    server_physical = PhysicalLayer('localhost', 12345, is_server=True)
    server_datalink = DataLinkLayer(b'\x11\x11\x11\x11\x11\x11', b'\x22\x22\x22\x22\x22\x22')
    server_network = NetworkLayer(b'\x0a\x00\x00\x01', b'\x0a\x00\x00\x02')
    server_transport = TransportLayer()
    server_session = SessionLayer(1234)
    server_presentation = PresentationLayer(b'secret')
    server_application = ApplicationLayer()


    print("Server setup 2")
    server_physical.upper_layer = server_datalink
    server_datalink.lower_layer = server_physical
    server_datalink.upper_layer = server_network
    server_network.lower_layer = server_datalink
    server_network.upper_layer = server_transport
    server_transport.lower_layer = server_network
    server_transport.upper_layer = server_session
    server_session.lower_layer = server_transport
    server_session.upper_layer = server_presentation
    server_presentation.lower_layer = server_session
    server_presentation.upper_layer = server_application
    server_application.lower_layer = server_presentation

    server_physical.start()

    # Client setup
    print("Client setup")
    client_physical = PhysicalLayer('localhost', 12345, is_server=False)
    client_datalink = DataLinkLayer(b'\x22\x22\x22\x22\x22\x22', b'\x11\x11\x11\x11\x11\x11')
    client_network = NetworkLayer(b'\x0a\x00\x00\x02', b'\x0a\x00\x00\x01')
    client_transport = TransportLayer()
    client_session = SessionLayer(1234)
    client_presentation = PresentationLayer(b'secret')
    client_application = ApplicationLayer()

    client_physical.upper_layer = client_datalink
    client_datalink.lower_layer = client_physical
    client_datalink.upper_layer = client_network
    client_network.lower_layer = client_datalink
    client_network.upper_layer = client_transport
    client_transport.lower_layer = client_network
    client_transport.upper_layer = client_session
    client_session.lower_layer = client_transport
    client_session.upper_layer = client_presentation
    client_presentation.lower_layer = client_session
    client_presentation.upper_layer = client_application
    client_application.lower_layer = client_presentation

    client_physical.start()

    # Send a message from client to server
    message = "GET / HTTP/1.1\r\nHost: localhost\r\n\r\nHello, Server!"
    client_application.send_down(message)

    # Server receives the message
    import time
    time.sleep(1)  # Wait for the message to be processed
    print("Server received:", server_application.received_data)

if __name__ == "__main__":
    main()
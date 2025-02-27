# OSI Model Simulation

A Python implementation of the OSI (Open Systems Interconnection) model that demonstrates the layered network architecture through a practical client-server communication example.

## Overview

This project implements all seven layers of the OSI model:
1. Physical Layer - Handles raw bit transmission
2. Data Link Layer - Manages MAC addressing and frame creation
3. Network Layer - Handles IP addressing and routing
4. Transport Layer - Ensures reliable data transfer
5. Session Layer - Manages communication sessions
6. Presentation Layer - Handles data encryption and compression
7. Application Layer - Implements application-level protocols

## Features

- Complete implementation of all 7 OSI layers
- Client-server architecture using TCP sockets
- Data encapsulation and decapsulation at each layer
- Error detection and handling
- Debugging output for monitoring data flow
- Thread-safe implementation
- Resource cleanup on program termination

## Requirements

- Python 3.6 or higher
- Standard library modules:
  - socket
  - struct
  - zlib
  - threading
  - signal
  - time
  - sys

## Installation

Clone the repository:
```bash
git clone <repository-url>
cd osi-model
```

## Usage

Run the program:
```bash
python osi.py
```

The program will:
1. Start a server on localhost:12345
2. Create a client connection
3. Send an HTTP-like request through all OSI layers
4. Display the data flow through each layer

To stop the program, press Ctrl+C.

## Implementation Details

### Layer Classes

- `Layer`: Base class for all OSI layers
- `PhysicalLayer`: Handles physical transmission using TCP sockets
- `DataLinkLayer`: Implements MAC addressing and frame checking
- `NetworkLayer`: Manages IP addressing
- `TransportLayer`: Handles sequencing and checksums
- `SessionLayer`: Manages session IDs
- `PresentationLayer`: Implements encryption and compression
- `ApplicationLayer`: Processes HTTP-like messages

### Key Features

- **Error Handling**: Each layer includes validation and error checking
- **Debugging**: Detailed output showing data flow through layers
- **Modularity**: Clean separation between layers
- **Resource Management**: Proper cleanup of connections and threads

## Example Output

The program shows detailed information about:
- Server and client initialization
- Data flow through each layer
- Frame/packet contents
- Error detection
- Connection status


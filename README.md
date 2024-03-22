# Padawan Transport Protocol (PTP)

## Project Overview
The Padawan Transport Protocol (PTP) is an advanced transport layer protocol designed to ensure reliable data transmission over unreliable networks. It leverages the lightweight nature of UDP while incorporating the reliable delivery features akin to TCP, specifically crafted for unidirectional data transfer.

## Key Features
- **Reliable Delivery**: Implements a custom reliable delivery mechanism over UDP, including sequence numbering and acknowledgments.
- **Connection Management**: Establishes and terminates connections using a SYN/SYN-ACK/ACK pattern and a FIN/ACK sequence.
- **Packet Loss Handling**: Simulates packet loss scenarios to validate the protocol's reliability and robustness.
- **Data Segmentation**: Adheres to predefined maximum segment size constraints for efficient data handling and transfer.

## Technical Specifications
- **Unidirectional Data Flow**: Ensures data is sent from a sender to a receiver without the capability for reverse data transmission within the same session.
- **Acknowledgment Processing**: Instantly processes acknowledgments for each data segment received without implementing delayed ACKs.
- **Command Line Configuration**: Facilitates setup through command-line arguments including host IP, port numbers, file paths, window size, and packet loss probability.

## Protocol Architecture
PTP operates in two main components:
- **Sender**: Handles the sending of data segments and processing of acknowledgments.
- **Receiver**: Manages the reception of data segments and the sending of acknowledgments.

Both components maintain detailed logs for diagnostic purposes and performance analysis.

## Usage Instructions
PTP is initiated via command-line interfaces for both sender and receiver components. For detailed usage, refer to the instructions provided within the project repository.

## Logging and Monitoring
- **Sender Log**: Records all sent and received segments, including packet type, sequence number, and acknowledgments.
- **Receiver Log**: Logs data reception and acknowledgment issuance, along with statistics on data received and segments handled.

## Development and Deployment
This project is developed in Python and is intended for deployment on systems that support Python 3.x. The protocol is designed with a focus on modularity and ease of integration into existing systems.

## Packet Loss Module
The Sender component includes a Packet Loss (PL) module to mimic network inconsistencies, thereby testing the protocol's capabilities in varying conditions.

## Contributing
Contributions to PTP are welcome. Developers interested in contributing to the project can follow the guidelines detailed in the contributing document.

## Contact
For queries or further information about the Padawan Transport Protocol project, please reach out to the project maintainers.

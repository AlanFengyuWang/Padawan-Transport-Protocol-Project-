# Padawan Transport Protocol (PTP)

## Introduction
PTP is a custom transport layer protocol built atop UDP to offer reliable data transmission. It is designed to simulate the operational procedures of TCP, including connection management and reliable packet delivery, while operating within the constraints and simplicity of the UDP protocol.

## Features
- **Reliable Transport**: Implements mechanisms for assured packet delivery despite the underlying unreliability of UDP.
- **Connection Establishment and Termination**: Adopts a three-way handshake for initiating communication sessions and a systematic closure procedure at the end of data transmission.
- **Packet Loss Simulation**: Features a built-in packet loss module, enabling the simulation of adverse network conditions to test the resilience and reliability of the protocol.
- **Unidirectional Data Flow**: Facilitates a one-way transfer of data from a sender to a receiver component, ensuring data integrity and order.

## Protocol Specifications
- **Handshake Protocol**: Utilizes SYN, SYN+ACK, and ACK signals for establishing a connection, akin to the initial handshake in TCP.
- **Transmission Mechanics**: Employs a simplified version of TCP's data transmission mechanics, including sequence numbers and cumulative acknowledgments.
- **Acknowledgment Strategy**: Incorporates immediate acknowledgment of received segments, streamlining the flow of communication.
- **Data Segmentation**: Adheres to a maximum segment size (MSS) to segment data into manageable units for transmission.

## Configuration Parameters
- **Maximum Segment Size (MSS)**: Specifies the largest payload size for PTP data segments.
- **Maximum Window Size (MWS)**: Defines the volume of data that can be sent unacknowledged, controlling the data flow.
- **Timeout**: Establishes a fixed timeout interval for the retransmission of packets, enhancing the protocol's reliability.
- **Packet Loss Probability (pdrop)**: Determines the likelihood of simulated packet loss to evaluate the protocol's performance under stress.

## Deployment Instructions
To run the PTP system, execute the sender and receiver programs with appropriate command-line arguments that configure the network settings, file paths, and operational parameters.



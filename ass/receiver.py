'''
Author: Fengyu Wang
Zid: z5187561
Python Version: 3.9.1

Note: I have applied the special consideration, so this assignment is due to today 12:00pm, further
detail please refer to professor Salil.
'''
from socket import *
import sys
from struct import Struct
import struct
import time
import os

############################################################ 
#################### Global Variables ###################### 
############################################################ 
global SYN  #initially, SYN is 1 when forming three ways handshakes
SYN = 0
global ACK
global SEQ_NUM
global BEGINNING_BUFFER_INDEX
global AMOUNT_DATA_RECEIVED
global NUM_DATA_SEMENTS
global NUM_DUPLICATED_SEGMENTS

# Colored printing functions for strings that use universal ANSI escape sequences.
# fail: bold red, pass: bold green, warn: bold yellow, 
# info: bold blue, bold: bold white

class ColorPrint:

    @staticmethod
    def print_fail(message, end = '\n'):
        sys.stderr.write('\x1b[1;31m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_pass(message, end = '\n'):
        sys.stdout.write('\x1b[1;32m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_warn(message, end = '\n'):
        sys.stderr.write('\x1b[1;33m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_info(message, end = '\n'):
        sys.stdout.write('\x1b[1;34m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_bold(message, end = '\n'):
        sys.stdout.write('\x1b[1;37m' + message.strip() + '\x1b[0m' + end)

############################################################ 
#################### MAIN FUNCTIONS ######################## 
############################################################ 

def receiver(receiver_port, file_received):
    '''
    Functions:
    Receiver sends cumulative acknowledgements like GBN.
    Receivers may not drop out-of-sequence pakcets like SR, so it will buffer all unordered data.
    '''
    #connection setup

    serverSocket = socket(AF_INET, SOCK_DGRAM)
    serverSocket.bind(('127.0.0.1', receiver_port))

    print("Waiting for connection..")
    while(1):
        if respond_handshakes('127.0.0.1', receiver_port, serverSocket) == True:
            break
        else:
            print("Connection failed, reconnecting..")
    print("Connection estabalished, waiting for receiving file..")

    #Firstly, receive the MWS
    MWS, MSS, num_segments, num_windows, window_leftover_size_bytes,\
    window_leftover_beginning_index, segement_left_over_size_bytes, segment_leftover_beginning_index, file_size = \
    receive_MWS_MSS_segment_leftover_from_client(serverSocket)

    global ACK
    global BEGINNING_BUFFER_INDEX
    global AMOUNT_DATA_RECEIVED
    global NUM_DATA_SEMENTS
    global NUM_DUPLICATED_SEGMENTS

    previous_ack = ACK
    BEGINNING_BUFFER_INDEX = previous_ack
    buffer = {1:None, 2:None, 3:None, 4:None, 5:None}
    clientAddress = 0
    AMOUNT_DATA_RECEIVED = 0
    NUM_DATA_SEMENTS = 0
    NUM_DUPLICATED_SEGMENTS = 0
    is_last_segment = False
    while True:
        #1)read file, response with ACK, it should expect the correct size of the segment (MWS, given by sender),
        #and if the segment size is not correct, it will send the old ACK indicate negative acknowledgement
        try:
            receive_segment_format = receive_segment_format_producer(MSS)
            seq_num, data, clientAddress, receive_type  = receive_segment(serverSocket, receive_segment_format)
            ColorPrint.print_bold(f"seq_num = {seq_num}, prev ack = {previous_ack}")
        except:
            receive_segment_format = receive_segment_format_producer(segement_left_over_size_bytes)
            ColorPrint.print_bold(f"receive_segment_format = {receive_segment_format}")
            seq_num, data, clientAddress, receive_type  = receive_segment(serverSocket, receive_segment_format)
            is_last_segment = True
        ColorPrint.print_bold(f"data = {data}")

        #connection teardown
        if receive_type == 'FINs':
            write_report(AMOUNT_DATA_RECEIVED, NUM_DATA_SEMENTS, NUM_DUPLICATED_SEGMENTS)
            ACK += 1
            break

        #store in the buffer if the size is allowed
        if (seq_num <= previous_ack + MSS * 5 and seq_num >= BEGINNING_BUFFER_INDEX):
            #write the first in ordered packet to the file
            store_to_buffer(buffer, seq_num, data, MSS)

        #update the expected seq num
        #when receive the correct seq_num, write the buffer to the file, then clean the buffer 
        # ColorPrint.print_bold(f"seq_num = {seq_num}, prev ack = {previous_ack}")
        if (previous_ack == seq_num):
            print(buffer)
            previous_ack = previous_ack + len(data)
            SEQ_NUM = previous_ack
            # ColorPrint.print_pass(f"received_data = {data}, received seq = {seq_num}")
            # ColorPrint.print_pass(f"send previous_ack = {previous_ack}")
        
            #write it to the FileReceived if it's not repeated
            if len(data) == MSS or (len(data) == segement_left_over_size_bytes and is_last_segment == True):
                write_file(buffer, MSS)

        send_acknowledgement(serverSocket, clientAddress, previous_ack)

    #connection teardown
    disconnect('127.0.0.1', receiver_port, serverSocket, clientAddress)

############################################################ 
#################### Helper FUNCTIONS ######################
############################################################ 
def respond_handshakes(receiver_host_ip, receiver_port, serverSocket):
    '''
    It establish the three ways handshakes,
    return True if success, else return false
    '''
    #receiving from the client's first handshake request
    message, clientAddress = serverSocket.recvfrom(2048)
    syn_bit, client_seq = struct.unpack('ii', message)

    #second_way: when receive SYN from the client, it will send SYN = 1, ACK + 1, client_seq = 1
    global SYN
    global ACK
    global SEQ_NUM

    SYN = 1                                 #set SYN to 1
    SEQ_NUM = 1                             #initialize seq num as 1
    ACK = client_seq + 1                    #ACK = seq + 1

    #if the the SYNbit is 1, then responding back with the connection request.
    if syn_bit == 1:
        #send the first acknolwedgement to sender
        payload = struct.pack('iii', SYN, ACK, SEQ_NUM)   #here struct includes SYN, 1(The SYN value), (seq #)
        serverSocket.sendto(payload, clientAddress)
    else:
        print("Have not received the acknowledgement from the client in the second handshake, cannot connect..")
        return False

    #receiving the third way handshake
    message, clientAddress = serverSocket.recvfrom(2048)
    syn_bit, ack, client_seq = struct.unpack('iii', message)
    if syn_bit == 0:
        return True
    else:
        print("Have not received the acknowledgement from the client in the third handshake, cannot connect..")
        return False

def receive_MWS_MSS_segment_leftover_from_client(serverSocket): 
    data, clientAddress = serverSocket.recvfrom(2048)

    MWS, MSS, num_segments, num_windows, window_leftover_size_bytes, \
    window_leftover_beginning_index, segement_left_over_size_bytes, \
    segment_leftover_beginning_index, file_size = struct.unpack('iiiiiiiii', data)
    return (MWS, MSS, num_segments, num_windows, window_leftover_size_bytes, window_leftover_beginning_index, segement_left_over_size_bytes, segment_leftover_beginning_index, file_size)

def receive_segment_format_producer(MSS):
    size_string_format = str(MSS) + 's'
    receive_type = '4s'
    seq_format = 'i'      #here header includes SEQ
    total_format = seq_format + size_string_format + receive_type
    return total_format

def receive_segment(serverSocket, receive_segment_format):
    '''
    It returns the content of the received segment
    '''
    message, clientAddress = serverSocket.recvfrom(2048)
    ColorPrint.print_bold(f"payload = {message}")
    received_seq_num, received_data, received_data_type = struct.unpack(receive_segment_format, message)
    received_data = received_data.decode('utf-8')
    received_data_type = received_data_type.decode('utf-8')
    return (received_seq_num, received_data, clientAddress, received_data_type)
        
def send_acknowledgement(serverSocket, clientAddress, ack):
    payload = struct.pack('i', ack)
    serverSocket.sendto(payload, clientAddress)

def write_file(buffer, MSS):
    global BEGINNING_BUFFER_INDEX
    global AMOUNT_DATA_RECEIVED
    global NUM_DATA_SEMENTS

    #check if the file exits
    if os.path.exists("FileReceived.txt"):
        append_write = 'a'
    else:
        append_write = 'w'

    text_file = open("FileReceived.txt", append_write)
    the_null_index = 0
    # null_exist = False

    for i in buffer:
        if buffer[i] == None:
            # null_exist = True
            the_null_index = i
            break
        print(f"writing buffer[i] {buffer[i]}")
        AMOUNT_DATA_RECEIVED += MSS
        NUM_DATA_SEMENTS += 1

        text_file.write(buffer[i])
        BEGINNING_BUFFER_INDEX += MSS
    
    #update the buffer by moving to the left until there's null
    shift_units = the_null_index - 1
    #in the case there's a null and the first is not null
    i = 1
    while buffer[1] != None:
        for i in range(1, 5):
            #make sure it will exit the loop in the case all window size is full 
            tmp = buffer[i+1]
            if i + 1 == 5:
                buffer[i+1] = None
            buffer[i] = tmp

    text_file.close()

def write_report(amount_data_received, num_data_segments, num_duplicate_segment_received):
    '''
    Here the amount of data received do not include retransmitted data
    '''
    #check if the file exits
    if os.path.exists("Receiver_log.txt.txt"):
        append_write = 'a'
    else:
        append_write = 'w'

    text_file = open("Receiver_log.txt", append_write)
    f = open("Receiver_log.txt", append_write)


    result = "Amount of data received in bytes: " + str(amount_data_received) + '\n' + \
    "Amount of segments received: " + str(num_data_segments) + '\n' + \
    "num_duplicate_segment_received: " + str(num_duplicate_segment_received)
    f.write(result)
    f.close()

def store_to_buffer(buffer, seq_num, data, MSS):
    '''
    Seq_num_received decide where it stores. seq_num that equals to previous_ack is stored in 1,
    seq_num that equals to the previous_ack + len(data) is stored in 2 and so on.
    '''
    global BEGINNING_BUFFER_INDEX
    global NUM_DUPLICATED_SEGMENTS
    for i in buffer:
        # print(f"seq_num = {seq_num}, previous_ack = {previous_ack}, data length = {len(data)}, i = {i}")
        if data in buffer.values():
            NUM_DUPLICATED_SEGMENTS += 1

        if seq_num == BEGINNING_BUFFER_INDEX + len(data) * (i-1):
            buffer[i] = data


def disconnect(receiver_host_ip, receiver_port, serverSocket, clientAddress):
    global ACK
    global SEQ_NUM

    payload = struct.pack('i', ACK)  
    serverSocket.sendto(payload, (receiver_host_ip, receiver_port))

    #second time
    message = "FINs"
    payload = struct.pack('i4s', SEQ_NUM, message.encode('utf-8'))  
    serverSocket.sendto(payload, (receiver_host_ip, receiver_port))

    new_message, clientAddress = serverSocket.recvfrom(2048)
    seq_received = struct.unpack('i', new_message)  
    return True

if __name__ == '__main__':
    receiver_port, FileReceived = sys.argv[1], sys.argv[2]
    receiver(int(receiver_port), FileReceived)


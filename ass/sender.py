'''
Author: Fengyu Wang
Zid: z5187561
Python Version: 3.9.1

Note: I have applied the special consideration, so this assignment is due to today 12:00pm
'''
from socket import *
import threading
import time
import datetime
import struct
import sys
import random 
import os

############################################################ 
#################### Global Variables ###################### 
############################################################ 
global SYN  #initially, SYN is 1 when forming three ways handshakes
global ACK
global SEQ_NUM

UPDATE_INTERVAL = 0.1

import sys

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

#threading
# t_lock = threading.Condition()

############################################################ 
#################### MAIN FUNCTIONS ######################## 
############################################################ 
def sender(receiver_host_ip, receiver_port, filetosend, MWS, MSS, timeout,\
pdrop, seed_num):
    '''
    Functions:
    Sender maintains a single timer, retransmit packets when:
        1)perform fast retransmit when receives three duplicated ACK from the senders
    Sender uses GBN when sending data.
        
    Input:
        MWS(Maximum segment size): The maximum number of bytes of data that your PTP segment can contain. 
        In other words, MSS counts data ONLY and does NOT include header.
    '''
    #connect
    clientSocket = socket(AF_INET, SOCK_DGRAM)

    clientSocket.settimeout(timeout)

    #start the timer
    start_time = time.time()
    random.seed(seed_num)           #seed the random numbers

    #send three ways handshakes
    if send_handshakes_request(receiver_host_ip, receiver_port, clientSocket, start_time) == True:
        print("Connection established, now sending file..")

    #read file, divided into chunks and then send to receiver.py
    file = open(filetosend, "r")
    file_content = file.read()

    #send file
    send_file(file_content, clientSocket, receiver_host_ip, receiver_port, MWS, MSS, timeout, start_time, \
    pdrop, seed_num)
    print("close connection")
    close_connection(receiver_host_ip, receiver_port, clientSocket, start_time, MSS)


############################################################ 
#################### Helper FUNCTIONS ######################
############################################################ 
def send_handshakes_request(receiver_host_ip, receiver_port, clientSocket, start_time):
    '''
    receiver send the first handshake, wait for the second handshake, then send the third handshake
    '''
    global SYN
    global SEQ_NUM
    global ACK
    ACK = 0
    SYN = 1             #initliaze SYN as 1
    SEQ_NUM = 0         #initialize SEQ as 0

    #send SYN, 1(SYN value), seq num 0, 
    print("Initializing connection")
    payload = struct.pack('ii', SYN, SEQ_NUM)   #here struct includes SYN, 1(The SYN value), (seq #)

    clientSocket.sendto(payload, (receiver_host_ip, receiver_port))
    #get the time and write to the report

    write_report('snd', start_time, 'S', SEQ_NUM, 0, ACK)   #here sending the ACK of the sender


    #after received SYN, make SYN zero, send ACK, otherwise resent SYN after timeout
    payload, serverAddress = clientSocket.recvfrom(2048)
    syn, ack, server_seq_num = struct.unpack('iii', payload)

    #get the time and write to the report
    write_report('rcv', start_time, 'SA', SEQ_NUM, 0, ack)  #here receive ack from the receiver

    #sending the third handshake, ACK is still 1, ACKnum = seq_num + 1
    SEQ_NUM = SEQ_NUM + 1                           #client_isn + 1
    ACK = server_seq_num + 1                        #ACK = server_isn + 1
    SYN = 0                                         #SYN = 0

    payload = struct.pack('iii', SYN, ACK, SEQ_NUM) #here struct includes SYN, 1(The SYN value), (seq #)
    clientSocket.sendto(payload, (receiver_host_ip, receiver_port))

    #get the time and write to the report
    write_report('snd', start_time, 'A', SEQ_NUM, 0, ACK)   #here the ACK has been updated as the  received_ack + 1

    return True


def send_file(file_content, clientSocket, receiver_host_ip, receiver_port, MWS, MSS, timeout, start_time, \
pdrop, seed_num):
    '''
    divide data into chunks and send each chunks to the receiver
    '''
    #global varialbes
    global ACK
    global SEQ_NUM

    #For each window, send all segments, if receive more than 3 duplicated ACKs, resend the whole window of pakcets
    #get num_segments
    num_segments, num_windows = generate_NumSegments_Num_windows(file_content, MSS, MWS)

    #find the window_left_over_size_bytes
    window_leftover_size_bytes = len(file_content) - MWS * int(len(file_content) / (MWS))     #size of segment * size of windows(in bytes) *number of windows
    window_leftover_beginning_index = len(file_content) - window_leftover_size_bytes

    #find the segement_left_over_size_bytes
    segement_left_over_size_bytes = window_leftover_size_bytes - MSS * int(window_leftover_size_bytes / MSS)  #the leftover size - size of segment * num of segments leftover
    segment_leftover_beginning_index = len(file_content) - segement_left_over_size_bytes

    #send MSW, MSS over
    send_MWS_MSS_segment_leftover_to_server(MWS, MSS, num_segments, num_windows, window_leftover_size_bytes, \
    window_leftover_beginning_index, segement_left_over_size_bytes, segment_leftover_beginning_index, receiver_host_ip, receiver_port, clientSocket, len(file_content))
    
    window_index = 0
    segment_index = window_index
    beginning_window_index = 0

    '''
    If we reach to the leftover parts, we shrink the size of the windows and segments. Otherwise, send it based
    on the size of MWS and MSS

    Fast retransmission: 
    If there are 3 duplicate ACKs for the same data, resend unacked segment with smallest seq #
    when it receives the acknowledgement from the Left most segment in a window, the window move forward by 1.
    when it receives the acknowledgement from the Right most segmetn in a window, the window move forward by the size of the window.
        
    if it has received the correct acknowledgement, window moves to the right by one unit. Otherwise, continue resending. 
    '''
    #wait for acknowledgements
    segment_send_index = beginning_window_index + MWS - MSS        #the segment we send is the last packet in the window when we move the window
    expected_ack_num = MWS + 1      
    first_time_send_window_true = True
    beginning_window_index = 0
    duplicated_ack = 0
    prev_ack = 0
    while expected_ack_num <= len(file_content) + 1:
        try:    
            #if it's the first time, find the index of the most recent 
            if first_time_send_window_true:
                first_time_send_window_true = False
                raise Exception("sending the first window")

            #wait for receive
            ack_received = receive_acknowledgement(clientSocket, start_time, SEQ_NUM, MSS)

            #when receive the ack for the last segment, break
            if ack_received >= len(file_content) + 1:
                break

            #the sender keep waiting for receiving the ACK, if it is the right ACK, the window immediately
            #slide by n unit, otherwise, it will ignore the ACK until either it receives the right ACK or
            #timeout
            
            #Here if the sender receives a high ACK and hasn't received the low ACK, it means
            #that the receiver has received all previous data, only the its acknowledgement got lost
            #Action: sliding the window and send new data
            # ColorPrint.print_bold(f"ack_received = {ack_received}, expected_ack_num = {expected_ack_num}")

            #update the SEQ_NUM to the last packet in a window if it's the first time
            
            while (ack_received >= expected_ack_num):
                if beginning_window_index < len(file_content) - MWS:
                    beginning_window_index += MSS                                      #slide window by one packet
                new_segment_send_index = beginning_window_index + MWS - MSS        #the segment we send is the last packet in the window when we move the window 

                #here only send the last packet, so ignore all packets before the last packet
                send_segment_PL(pdrop, seed_num, file_content, new_segment_send_index, MSS, MWS, SEQ_NUM, clientSocket,\
                receiver_host_ip, receiver_port, start_time, ACK, segment_leftover_beginning_index, segement_left_over_size_bytes) 
                if new_segment_send_index == segment_leftover_beginning_index and segement_left_over_size_bytes != 0:
                    expected_ack_num += segement_left_over_size_bytes
                else: 
                    expected_ack_num += MSS

            #for fast retransmission
            if ack_received < expected_ack_num:
                if prev_ack == ack_received:
                    duplicated_ack += 1

                if duplicated_ack == 3:
                    ColorPrint.print_pass(f"fast retransmit, seq_num = {ack_received}")
                    tmp = SEQ_NUM
                    SEQ_NUM = ack_received
                    send_segment_PL(pdrop, seed_num, file_content, new_segment_send_index, MSS, MWS, SEQ_NUM, clientSocket,\
                    receiver_host_ip, receiver_port, start_time, ACK, segment_leftover_beginning_index, segement_left_over_size_bytes) 
                    SEQ_NUM = tmp
                    duplicated_ack = 0
            prev_ack = ack_received
            
        #if timeout
        except:
            #reset SEQ_NUM
            SEQ_NUM = beginning_window_index + 1    #here plus 1 because in the handshake there's 1 sequence number
            ColorPrint.print_warn(f"SEQ_NUM = {SEQ_NUM}, beginning_window_index = {beginning_window_index}, MWS = {MWS}")
            send_window_of_packets(beginning_window_index, beginning_window_index, file_content, MSS, MWS, SEQ_NUM,\
            clientSocket, receiver_host_ip, receiver_port, timeout, pdrop, seed_num, start_time, ACK, segment_leftover_beginning_index, segement_left_over_size_bytes,\
            window_leftover_size_bytes)

            if beginning_window_index == 0:
                SEQ_NUM = beginning_window_index + 1
            continue


def send_segment_PL(pdrop, seed_num, file_content, segment_index, MSS, MWS, seq_num, clientSocket,\
receiver_host_ip, receiver_port, start_time, ACK, segment_leftover_beginning_index, segement_left_over_size_bytes):
    '''
    Send segment out if the random num is greater than pdrop
    '''
    global SEQ_NUM
    #check if we drop the data
    if not packet_lost(pdrop, seed_num):
        #if it's the last index, only send the size 
        if segement_left_over_size_bytes != 0 and segment_index == segment_leftover_beginning_index:
            # ColorPrint.print_info(f"==> enter the condition for the last segment, segment_index = {segment_index}, data = {file_content[segment_index:segment_index+segement_left_over_size_bytes]}")
            send_segment = file_content[segment_index:segment_index+segement_left_over_size_bytes]
            send_segment_format = send_segment_format_generator(segement_left_over_size_bytes)
            payload = struct.pack(send_segment_format, SEQ_NUM, send_segment.encode('utf-8'), 'DATA'.encode('utf-8'))
            # ColorPrint.print_pass(f"*==>send the segment {send_segment}, SEQ_NUM = {SEQ_NUM}, payload = {payload}")
            clientSocket.sendto(payload, (receiver_host_ip, receiver_port))
            clientSocket.sendto(payload, (receiver_host_ip, receiver_port)) #send it twice 
            
        else:
            send_segment = file_content[segment_index:segment_index+MSS]  #here we are excluding the size of the header
            send_segment_format = send_segment_format_generator(MSS)
            #send data
            # ColorPrint.print_info(f"==>send the segment {send_segment}, SEQ_NUM = {SEQ_NUM} ")
            payload = struct.pack(send_segment_format, SEQ_NUM, send_segment.encode('utf-8'), 'DATA'.encode('utf-8'))
            clientSocket.sendto(payload, (receiver_host_ip, receiver_port))

        #update the report
        write_report('snd', start_time, 'D', SEQ_NUM, MSS, ACK)  

    else:
        send_segment = file_content[segment_index:segment_index+MSS]
        write_report('drop', start_time, 'D', SEQ_NUM, MSS, ACK)

    #update SEQ_NUM and the temp_seq_num
    update_SEQ_NUM(MSS, segment_index, segement_left_over_size_bytes, segment_leftover_beginning_index)


def send_window_of_packets(segment_index, beginning_window_index, file_content, MSS, MWS, next_seq_num, \
clientSocket, receiver_host_ip, receiver_port, timeout, pdrop, seed_num, start_time, ACK, segment_leftover_beginning_index, \
segement_left_over_size_bytes, window_leftover_size_bytes):
    '''
    Send whole window of packets.
    If the file content size is smaller than the window size, then we only send a smaller num of packet groups.

    If it's the last window and the size of the window is smaller than usual window size, then it only go through all packets
    in that window.
    '''

    if window_leftover_size_bytes != 0 and segment_index >= len(file_content) - window_leftover_size_bytes:
        #if it's not the last packet, send over the packet with the size of MSS
        while segment_index < segment_leftover_beginning_index:
            send_segment_PL(pdrop, seed_num, file_content, segment_index, MSS, MWS, next_seq_num, clientSocket,\
            receiver_host_ip, receiver_port, start_time, ACK, segment_leftover_beginning_index, segement_left_over_size_bytes)
            segment_index += MSS
        
        #here is when the segment_index reach to the last packet which might have a different sizes
        # ColorPrint.print_info(f"=> check the following are equal:segment_index = {segment_index}, segment_leftover_beginning_index = {segment_leftover_beginning_index}")
        send_segment_PL(pdrop, seed_num, file_content, segment_index, MSS, MWS, next_seq_num, clientSocket,\
        receiver_host_ip, receiver_port, start_time, ACK, segment_leftover_beginning_index, segement_left_over_size_bytes)
        segment_index += segement_left_over_size_bytes        #Here for the last segment that has a different size, increment segment index by the size of the last segment


    else:
        while segment_index < beginning_window_index + MWS:
            # ColorPrint.print_fail(f"segment_index = {segment_index}, beginning_window_index + MWS = {beginning_window_index + MWS}")
            # print(f"segment_index = {segment_index}, beginning_window_index + MWS = {beginning_window_index + MWS}")
            #for the first segment of each window, set the timer, other segments do not require timer
            send_segment_PL(pdrop, seed_num, file_content, segment_index, MSS, MWS, next_seq_num, clientSocket,\
            receiver_host_ip, receiver_port, start_time, ACK, segment_leftover_beginning_index, segement_left_over_size_bytes)

            #increment segment_index
            segment_index += MSS
    
    segment_index = beginning_window_index          #reset segment index to the start of the window


def receive_acknowledgement(clientSocket, start_time, next_seq_num, MSS):
    '''
    Receive the acknowledgement from receiver, ACK = SEQ + Data size or ACK = next_seq num
    Output:
        received_ack (int)
    '''
    response, serverAddress = clientSocket.recvfrom(2048)
    received_ack = struct.unpack('i', response)
    write_report('rcv', start_time, 'D', next_seq_num, MSS, received_ack[0])   #here sending the ACK of the receiver, which is the previous sequence number
    return received_ack[0]

def send_segment_format_generator(MSS):
    '''
    Return 'MSS s i'
    '''
    seq_format = 'i'                #here header includes ACK and SEQ
    size_string_format = str(MSS) + 's'
    receive_type = '4s'

    send_segment_format = seq_format + size_string_format + receive_type
    return send_segment_format

def write_report(type_actions, start_time, type_packet, seq_num, num_bytes, ack):
    global BEGINNING_BUFFER_INDEX

    #check if the file exits
    if os.path.exists("Sender_log.txt"):
        append_write = 'a'
    else:
        append_write = 'w'

    text_file = open("Sender_log.txt", append_write)

    time_used = time.time() - start_time
    time_used = round(time_used, 2)
    time_used = str(time_used)
    f = open("Sender_log.txt", "a")
    if len(type_actions) == 3:
        if len(time_used) < 4:
            result = type_actions + '\t\t' + str(time_used) + '\t\t' + type_packet + '\t' + str(seq_num) + '\t' + str(ack) + '\n'
        else:
            result = type_actions + '\t\t' + str(time_used) + '\t' + type_packet + '\t' + str(seq_num) + '\t' + str(ack) + '\n'
    else:
        if len(time_used) < 4:
            result = type_actions + '\t' + str(time_used) + '\t\t' + type_packet + '\t' + str(seq_num) + '\t' + str(ack) + '\n'
        else: 
            result = type_actions + '\t' + str(time_used) + '\t' + type_packet + '\t' + str(seq_num) + '\t' + str(ack) + '\n'
    f.write(result)
    f.close()

def packet_lost(pdrop, seed_num):
    '''
    With the probability pdrop drop the datagram.
    with the probability (1 - pdrop), forward the datagram

    if the choosen number is greater than pdrop transmit the packet (return True), else the packet is lost (return False)
    '''
    #generate a random number
    if (random.random() > pdrop):
        return False     #here indicate the packet is transmitted
    else:
        return True    #Here indicate the packet is lost.

def generate_NumSegments_Num_windows(file_content, MSS, MWS):
    if (len(file_content) % MSS == 0):
        num_segments = len(file_content) / MSS
    else:
        num_segments = int(len(file_content) / MSS) + 1
    
    #get num_windows
    if (len(file_content) % (MSS * MWS) == 0):
        num_windows = len(file_content) / (MSS * MWS)
    
    else:
        num_windows = int(len(file_content) / (MSS * MWS)) + 1
    return (num_segments, num_windows)

def update_SEQ_NUM(MSS, segment_index, segement_left_over_size_bytes, segment_leftover_beginning_index):
    global SEQ_NUM
    #if it's the last index, only send the size 
    if (segement_left_over_size_bytes != 0 and segment_index == segment_leftover_beginning_index):
        SEQ_NUM += segement_left_over_size_bytes
    else:
        SEQ_NUM += MSS

def send_MWS_MSS_segment_leftover_to_server(MWS, MSS, num_segments, num_windows, window_leftover_size_bytes, 
window_leftover_beginning_index, segement_left_over_size_bytes, segment_leftover_beginning_index, receiver_host_ip, receiver_port, clientSocket, file_size):
    payload = struct.pack('iiiiiiiii', MWS, MSS, int(num_segments), int(num_windows), int(window_leftover_size_bytes), 
    int(window_leftover_beginning_index), int(segement_left_over_size_bytes), int(segment_leftover_beginning_index), file_size)
    print("sendingding")
    clientSocket.sendto(payload, (receiver_host_ip, receiver_port))

def close_connection(recesiver_host_ip, receiver_port, clientSocket, start_time, MSS):
    global SEQ_NUM
    global ACK

    #send SYN, 1(SYN value), seq num 0, 
    send_format = send_segment_format_generator(MSS)

    payload = struct.pack(send_format, SEQ_NUM, "EMPTY DATA".encode('utf-8'), 'FINs'.encode('utf-8'))  
    clientSocket.sendto(payload, (receiver_host_ip, receiver_port))
    write_report('snd', start_time, 'F', SEQ_NUM, 0, ACK)   

    payload, serverAddress = clientSocket.recvfrom(2048)
    ACK = struct.unpack('i', payload)
    write_report('rcv', start_time, 'FA', SEQ_NUM, 0, ACK)  
    
    #second time
    payload, serverAddress = clientSocket.recvfrom(2048)
    result = struct.unpack('i', payload)
    ACK = result[0]
    ACK += 1 
    new_payload = struct.pack('i4s', ACK, 'ACKs'.encode('utf-8'))  
    print(new_payload)
    clientSocket.sendto(new_payload, (receiver_host_ip, receiver_port))

    write_report('rcv', start_time, 'A', SEQ_NUM, 0, ACK) 
    return True
    

if __name__ == '__main__':
    #get arguments
    receiver_host_ip, receiver_port, filetosend, MWS, MSS, timeout,\
    pdrop, seed_num = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],\
    sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8]

    sender(receiver_host_ip, int(receiver_port), filetosend, int(MWS), int(MSS), float(timeout),\
    float(pdrop), int(seed_num))
    

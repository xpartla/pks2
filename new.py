import binascii
import math
import os
import socket
import struct
import threading
import time
import random

def client_setup():
    c_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_info = (input("Input server ADDRESS"), int(input("Input server PORT")))
    c_socket.sendto(str.encode(""), server_info)
    c_socket.settimeout(60)
    data, server_info[0] = c_socket.recvfrom(1500)
    data = data.decode()
    if data == "1":
        print("Connection Successful, \nServer address: ", server_info[0],"\nServer port: ", server_info[1])
        run_client(c_socket, server_info[0])
    else:
        print("Something went wrong")

def run_client(socket, server_ip):
    print("WEEEEEEEEE")
    while True:
        mode = input("t - text, \nf - file, \ns - switch roles \nq - quit")
        if mode == 't':
            send_text(socket, server_ip)
        elif mode == 'q':
            return
        else:
            print("Wrong input, try again")

def send_text(socket, server_ip):

    msg = input("Input your message: ")
    fragment_size = 0
    while fragment_size >= 64965 or fragment_size <= 0:     #TODO: Change max fragment size
        fragment_size = int(input("Input Fragment Size (max 64965B): "))

    #asi zle pomenovana variable fragment_amount -> packet_number? not sure
    fragment_amount = math.ceil(len(msg)/fragment_size)
    print("Fragment amount: ", fragment_amount)

    include_error = input("Include error?(Y/N):")

    while True:
        if len(msg) == 0:
            break
        send = msg[:fragment_size]
        send = str.encode(send)

        header = struct.pack("c", str.encode("2")) + struct.pack("HH", len(send), fragment_amount)
        crc = binascii.crc_hqx(header + send, 0)

        if include_error == 'Y' or include_error == 'y':
            if random.random() < 0.5: #TODO: Zisti preco random a nie straight up proste crc+1
                crc += 1

        header = struct.pack("c", str.encode("2")) + struct.pack("HHH", len(send), fragment_amount, crc)

        socket.sendto(header + send, server_ip)
        data, server_ip = socket.recvfrom(1500)

        try:
            socket.settimeout(10.0)
            data = data.decode()
            if data == "5":
                fragment_amount +=1
                msg = msg[fragment_size:]
            else:
                pass
        except (socket.timeout, socket.gaierror) as e:
            print(e)
            print("ERROR")
            return



def server_setup():
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #c_port = input("Input Client Port: ")
    s_socket.bind("", int(input("Input Client Port")))
    data, addr = s_socket.recvfrom(1500)
    s_socket.sendto(str.encode("1"), addr)
    run_server(s_socket, addr)

def run_server(socket, address):
    print("WEEEEEEEEEE")
    while True:
        mode = input("q - quit \ns - switch roles ")

        if mode == 'q':
            return

        if mode == 's':
            print("TBD")
        else:
            print("Server ON")

            try:
                socket.settimeout(60)

                while True:
                    data = socket.recv(1500)
                    info = str(data.decode())

                    message_type = info[:1]
                    #Text
                    if message_type == '1':
                        fragment_amount = info[1:]
                        print("Fragment amount: ", fragment_amount)
                        recieve_msg(fragment_amount, socket, "text")
                        break

                    #File
                    if message_type == '2':
                        fragment_amount = info[1:]
                        print("Fragment amount: ", fragment_amount)
                        recieve_msg(fragment_amount, socket, "file")
                        break
            except socket.timeout:
                print("TIMEOUT ERROR, server OFF")
                socket.close()
                return

def recieve_msg(fragment_amount, socket, msg_type):
    fragment_counter = 0
    overall_fragments = 0
    whole_msg = []
    while True:
        if int(fragment_amount) == 0:
            break

        data, address = socket.recvfrom(64965)
        msg = data[7:]
        length, fragment_number, crc_recieved = struct.unpack("HHH", data[1:7])
        header = struct.pack("c", str.encode("2")) + struct.pack("HH", len(msg), fragment_number)
        crc = binascii.crc_hqx(header + msg, 0)

        if crc == crc_recieved:
            print(f"Fragment Number{fragment_counter} accepted")
            fragment_counter += 1
            overall_fragments +=1

            if msg_type == "text":
                whole_msg.append(msg.decode())

            if msg_type == "file":
                whole_msg.append(msg)

            socket.sendto(str.encode("5"), address)

        else:
            print(f"Fragment Number{fragment_counter} rejected")
            socket.sendto(str.encode("3"), address)
            overall_fragments += 1

    print("Amount of damaged fragments: ", overall_fragments - fragment_counter)
    print("Amount of all recieved fragments: ", overall_fragments)
    print("Amount of accepted fragments: ", fragment_counter)

    if msg_type == "text":
        print("Message recieved: ", ''.join(whole_msg))

    if msg_type == "file":
        print("TBD")



if __name__ == '__main__':
    while True:
        mode = input("c - client\ns - server\nq - quit")
        if mode == 'c':
            client_setup()
        elif mode == 's':
            server_setup()
        elif mode == 'q':
            break
        else:
            print("Wrong input, try again:")
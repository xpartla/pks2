import binascii
import math
import os
import socket
import struct
import threading
import time
import random

KA_STATUS = True
CONN_INIT = "1"
DATA_TRANSFER = "2"
INCORRECT_DATA = "3"
KA_MSG = "4"
CORRECT_DATA = "5"
FILE_NAME = "6"
FILE_PATH = "7"

TEXT_MSG = "1"
FILE_MSG = "2"


def client_setup():
    global CONN_INIT
    while True:
        try:
            print(CONN_INIT)
            c_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_info = (input("Input server ADDRESS: "), int(input("Input server PORT: ")))
            addr = server_info[0]
            c_socket.sendto(str.encode(""), server_info)
            c_socket.settimeout(60)
            print("Waiting for response from server...")
            data, addr = c_socket.recvfrom(1500)
            data = data.decode()
            if data == CONN_INIT:
                print("Connection Successful, \nServer address: ", server_info[0],"\nServer port: ", server_info[1])
                run_client(c_socket, server_info)
        except (socket.timeout, socket.gaierror) as e:
            print(e)
            print("Something went wrong")
            continue

def run_client(socket, server_ip):
    print("You are now the CLIENT")
    keepalive = None
    global KA_STATUS

    while True:
        ka_start = input("Turn on KA? (server has to be in listening mode) (Y/N)")
        if ka_start == 'Y' or ka_start == 'y':
            KA_STATUS = True
            keepalive = ka_thread(socket, server_ip)


        mode = input("Choose function: \nt - text message, \nf - file transfer, \ns - switch roles \nq - quit")
        if mode == 't' or mode == 'T':
            if keepalive is not None:
                KA_STATUS = False
                keepalive.join()
            send_text(socket, server_ip)
        elif mode == 'f' or mode == 'F':
            if keepalive is not None:
                KA_STATUS = False
                keepalive.join()
            send_file(socket, server_ip)
        elif mode == 'q' or mode == 'Q':
            if keepalive is not None:
                KA_STATUS = False
                keepalive.join()
            print("Exiting client, setup new connection to server: ")
            break
        elif mode == 's' or mode == 'S':
            if keepalive is not None:
                KA_STATUS = False
                keepalive.join()
            switch(socket, server_ip)
        else:
            print("Wrong input, try again")

    return
def send_text(socket, server_ip):
    global CONN_INIT
    global CORRECT_DATA
    global TEXT_MSG

    msg = input("Input your message: ")
    fragment_size = 0
    while fragment_size >= 64965 or fragment_size <= 0:     #TODO: Change max fragment size
        fragment_size = int(input("Input Fragment Size (max 64965B): "))

    #asi zle pomenovana variable fragment_amount -> packet_number? not sure
    fragment_amount = math.ceil(len(msg)/fragment_size)
    print("Fragment amount: ", fragment_amount)

    comm_start = (TEXT_MSG + str(fragment_amount))
    comm_start = comm_start.encode('utf-8').strip()
    socket.sendto(comm_start, server_ip)

    include_error = input("Include error?(Y/N):")

    while True:
        if len(msg) == 0 or fragment_amount == 0:
            break
        send = msg[:fragment_size]
        send = str.encode(send)

        header = struct.pack("c", str.encode("2")) + struct.pack("HH", len(send), fragment_amount)
        crc = binascii.crc_hqx(header + send, 0)

        if include_error == 'Y' or include_error == 'y':
            if random.random() < 0.5: #teoreticky kazdy druhy packet je zly
                crc += 1

        header = struct.pack("c", str.encode("2")) + struct.pack("HHH", len(send), fragment_amount, crc)

        socket.sendto(header + send, server_ip)
        data, server_ip = socket.recvfrom(1500)

        try:
            socket.settimeout(10.0)
            data = data.decode()
            if data == CORRECT_DATA:
                fragment_amount +=1
                msg = msg[fragment_size:]
            else:
                pass
        except (socket.timeout, socket.gaierror) as e:
            print(e)
            print("ERROR")
            return


def send_file(socket, server_ip):
    global CORRECT_DATA
    global FILE_MSG
    global FILE_NAME
    global FILE_PATH

    file_name = input("Input the file name: ")
    file_path = input("Input the file path example -> (C:'\'PKS2'\'transfer)': ")
    frag_size = int(input("Input fragment size: "))

    while frag_size >= 64965 or frag_size <= 0:     #TODO: Change max fragment size
        frag_size = int(input("Input Fragment Size (max 64965B): "))

    size = os.path.getsize(file_name)
    print("File: ", file_name, "Size: ", size, "B")
    print("Path: ", os.path.abspath(file_name))
    file = open(file_name, "rb")
    file_size = os.path.getsize(file_name)
    frag_amount = math.ceil(file_size / frag_size)
    print("Fragment amount: ", frag_amount)

    msg = file.read()
    comm_start = (FILE_MSG + str(frag_amount))
    comm_start = comm_start.encode('utf-8').strip()
    socket.sendto(comm_start, server_ip)

    fname_msg = (FILE_NAME + str(file_name))
    fname_msg = fname_msg.encode('utf-8').strip()
    socket.sendto(fname_msg, server_ip)

    fpath_msg = (FILE_PATH + str(file_path))
    fpath_msg = fpath_msg.encode('utf-8').strip()
    socket.sendto(fpath_msg, server_ip)

    include_error = input("Include error?(Y/N):")

    while True:
        if len(msg) == 0:
            break
        send = msg[:frag_size]

        header = struct.pack("c", str.encode("2")) + struct.pack("HH", len(send), frag_amount)
        crc = binascii.crc_hqx(header + send, 0)

        if include_error == 'Y' or include_error == 'y':
            if random.random() < 0.5:  # kazdy druhy packet je zly
                crc += 1

        header = struct.pack("c", str.encode("2")) + struct.pack("HHH", len(send), frag_amount, crc)

        socket.sendto(header + send, server_ip)
        data, server_ip = socket.recvfrom(1500)

        try:
            socket.settimeout(10.0)
            data = data.decode()
            if data == CORRECT_DATA:
                frag_amount += 1
                msg = msg[frag_size:]
            else:
                pass
        except (socket.timeout, socket.gaierror) as e:
            print(e)
            print("ERROR")
            return

def server_setup():
    global CONN_INIT
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c_port = input("Input Client Port: ")
    info = ("", int(c_port))
    s_socket.bind(info)
    print("Waiting for Client to connect...")
    data, addr = s_socket.recvfrom(1500)
    s_socket.sendto(str.encode(CONN_INIT), addr)
    run_server(s_socket, addr)

def run_server(socket, address):
    global KA_MSG
    print("You are the SERVER")
    while True:
        mode = input("Choose operation \nq - quit \ns - switch roles \nEnter - listen ")

        if mode == 'q' or mode == 'Q':
            return

        if mode == 's' or mode == 'S':
            switch(socket, address)
        else:
            print("Server ON")

            try:
                socket.settimeout(60)

                while True:
                    while True:
                        data = socket.recv(1500)
                        info = str(data.decode())

                        if info == KA_MSG:
                            print("Server - Keep Alive")
                            socket.sendto(str.encode(KA_MSG), address)
                            info = ''
                            break
                        else:
                            break

                    message_type = info[:1]
                    #Text
                    if message_type == '1':
                        fragment_amount = info[1:]
                        print("Fragment amount: ", fragment_amount)
                        recieve_msg(fragment_amount, socket, "text", None, None)
                        break

                    #File
                    if message_type == '2':
                        fragment_amount = info[1:]
                        print("Fragment amount: ", fragment_amount)
                        fragment_amount, socket, msg_type, file_name, file_path = file_setup(fragment_amount, socket, "file")
                        print(file_path, file_name)
                        recieve_msg(fragment_amount, socket, "file", file_name, file_path)
                        break

            except socket.timeout:
                print("TIMEOUT ERROR, server OFF")
                socket.close()
                return


def file_setup(fragment_amount, s_socket, msg_type):
    global FILE_NAME
    global FILE_PATH
    file_name = None
    file_path = None
    while True:
        try:
            s_socket.settimeout(20)
            while True:
                while True:
                    data = s_socket.recvfrom(1500)
                    info = data[0].decode('utf-8')
                    my_type = info[0]
                    msg_content = info[1:]
                    print(my_type)
                    print(msg_content)
                    if my_type == FILE_NAME:
                        file_name = msg_content
                    elif my_type == FILE_PATH:
                        file_path = msg_content

                    if file_path is not None and file_path is not None:
                        return fragment_amount, s_socket, msg_type, file_name, file_path

        except socket.timeout:
            print("TIMEOUT ERROR, server OFF")
            socket.close()
            return


def recieve_msg(fragment_amount, s_socket, msg_type, file_name, file_path):
    global CORRECT_DATA
    global INCORRECT_DATA
    global FILE_NAME
    global FILE_PATH

    fragment_counter = 0
    overall_fragments = 0
    whole_msg = []

    while True:
        if int(fragment_amount) == fragment_counter:
            break
        data, address = s_socket.recvfrom(64965)
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

            s_socket.sendto(str.encode(CORRECT_DATA), address)

        else:
            print(f"Fragment Number{fragment_counter} rejected")
            s_socket.sendto(str.encode(INCORRECT_DATA), address)
            overall_fragments += 1

    print("Amount of damaged fragments: ", overall_fragments - fragment_counter)
    print("Amount of all received fragments: ", overall_fragments)
    print("Amount of accepted fragments: ", fragment_counter)

    if msg_type == "text":
        print("Message received: ", ''.join(whole_msg))

    if msg_type == "file":
        rename = input("Do you want to rename file? (Y/N)")
        if rename == 'Y' or rename == 'y':
            file_name = input("Input new file name: ")

        full_path = os.path.join(file_path, file_name)
        print("Do you want to use this path to save the file?", full_path)
        place = input("(Y/N): ")
        if place == 'Y' or place == 'y':
            file = open(full_path, "wb")
        else:
            print("Using default path")
            file = open(file_name, "wb")

        for frag in whole_msg:
            file.write(frag)
        file.close()
        print("Name: ", file_name, "Size: ", os.path.getsize(file_name), "B")
        print("Path where I want to save the file: ", file_path)
        print("Path: ", os.path.abspath(file_name))




def switch(socket, server_address):
    while True:
        mode = input("Choose your new role: \nc - client\ns - server\nq - quit")
        if mode == 'c' or mode == 'C':
            print("Changed role to CLIENT")
            run_client(socket, server_address)
        elif mode == 's' or mode == 'S':
            print("Changed role to SERVER")
            run_server(socket, server_address)
        elif mode == 'q' or mode == 'Q':
            break
        else:
            print("Wrong input, try again:")


def ka_thread(socket, s_addr):
    thread = threading.Thread(target=ka, args=(socket, s_addr))
    thread.daemon = True
    thread.start()
    return thread


def ka(socket, s_addr):
    while True:
        if not KA_STATUS:
            return
        try:
            socket.sendto(str.encode(KA_MSG), s_addr)
            data = socket.recv(1500)
            info = str(data.decode())
            if info == KA_MSG:
                print("Client - Keep Alive")
            else:
                print("Connection off")
                break
        except (socket.timeout, socket.error) as e:
            print(f"Error in keepalive: {e}")
            break
        time.sleep(5)

if __name__ == '__main__':
    while True:
        mode = input("Choose role: \nc - client\ns - server\nq - quit")
        if mode == 'c' or mode == 'C':
            client_setup()
        elif mode == 's' or mode == 'S':
            server_setup()
        elif mode == 'q' or mode == 'Q':
            break
        else:
            print("Wrong input, try again:")


#TODO: chyba na strane serveru, po prenose 1 spravy sa timeoutuje asi alebo neviem, neprijma dalsie spravy a na clientovy vypise timeout
#TODO: switch, keepalive, change header, fix var naming
#switch asi done, server chyba asi done?
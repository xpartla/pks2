import binascii
import math
import os
import socket
import struct
import threading
import time
import random

KA_STATUS = True


def client_setup():
    while True:
        try:
            c_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_info = (input("Input server ADDRESS"), int(input("Input server PORT")))
            addr = server_info[0]
            c_socket.sendto(str.encode(""), server_info)
            c_socket.settimeout(60)
            data, addr = c_socket.recvfrom(1500)
            data = data.decode()
            if data == "1":
                print("Connection Successful, \nServer address: ", server_info[0],"\nServer port: ", server_info[1])
                run_client(c_socket, server_info)
        except (socket.timeout, socket.gaierror) as e:
            print(e)
            print("Something went wrong")
            continue

def run_client(socket, server_ip):
    print("WEEEEEEEEE")
    keepalive = None
    global KA_STATUS

    while True:
        KA_STATUS = True
        keepalive = ka_thread(socket, server_ip)

        mode = input("t - text, \nf - file, \ns - switch roles \nq - quit")
        if mode == 't':
            if keepalive is not None:
                KA_STATUS = False
                keepalive.join()
            send_text(socket, server_ip)
        elif mode == 'f':
            if keepalive is not None:
                KA_STATUS = False
                keepalive.join()
            send_file(socket, server_ip)
        elif mode == 'q':
            if keepalive is not None:
                KA_STATUS = False
                keepalive.join()
            break
        elif mode == 's':
            if keepalive is not None:
                KA_STATUS = False
                keepalive.join()
            switch(socket, server_ip)
        else:
            print("Wrong input, try again")

    return
def send_text(socket, server_ip):

    msg = input("Input your message: ")
    fragment_size = 0
    while fragment_size >= 64965 or fragment_size <= 0:     #TODO: Change max fragment size
        fragment_size = int(input("Input Fragment Size (max 64965B): "))

    #asi zle pomenovana variable fragment_amount -> packet_number? not sure
    fragment_amount = math.ceil(len(msg)/fragment_size)
    print("Fragment amount: ", fragment_amount)

    comm_start = ("1" + str(fragment_amount))
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


def send_file(socket, server_ip):

    file_name = input("Input the file name: ")
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
    comm_start = ("2" + str(frag_amount))
    comm_start = comm_start.encode('utf-8').strip()
    socket.sendto(comm_start, server_ip)

    include_error = input("Include error?(Y/N):")

    while True:
        if len(msg) == 0:
            break
        send = msg[:frag_size]

        header = struct.pack("c", str.encode("2")) + struct.pack("HH", len(send), frag_amount)
        crc = binascii.crc_hqx(header + send, 0)

        if include_error == 'Y' or include_error == 'y':
            if random.random() < 0.5:  # TODO: Zisti preco random a nie straight up proste crc +1
                crc += 1

        header = struct.pack("c", str.encode("2")) + struct.pack("HHH", len(send), frag_amount, crc)

        socket.sendto(header + send, server_ip)
        data, server_ip = socket.recvfrom(1500)

        try:
            socket.settimeout(10.0)
            data = data.decode()
            if data == "5":
                frag_amount += 1
                msg = msg[frag_size:]
            else:
                pass
        except (socket.timeout, socket.gaierror) as e:
            print(e)
            print("ERROR")
            return

def server_setup():
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c_port = input("Input Client Port: ")
    info = ("", int(c_port))
    s_socket.bind(info)
    data, addr = s_socket.recvfrom(1500)
    s_socket.sendto(str.encode("1"), addr)
    run_server(s_socket, addr)

def run_server(socket, address):
    print("WEEEEEEEEEE")
    while True:
        mode = input("q - quit \ns - switch roles \nEnter - continue ")

        if mode == 'q':
            return

        if mode == 's':
            switch(socket, address)
        else:
            print("Server ON")

            try:
                socket.settimeout(60)

                while True:
                    while True:
                        data = socket.recv(1500)
                        info = str(data.decode())

                        if info == "4":
                            print("Ha Ha Ha Ha Stayin' alive")
                            socket.sendto(str.encode("4"), address)
                            info = ''
                            break
                        else:
                            break

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


def recieve_msg(fragment_amount, s_socket, msg_type):
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

            s_socket.sendto(str.encode("5"), address)

        else:
            print(f"Fragment Number{fragment_counter} rejected")
            s_socket.sendto(str.encode("3"), address)
            overall_fragments += 1

    print("Amount of damaged fragments: ", overall_fragments - fragment_counter)
    print("Amount of all received fragments: ", overall_fragments)
    print("Amount of accepted fragments: ", fragment_counter)

    if msg_type == "text":
        print("Message received: ", ''.join(whole_msg))

    if msg_type == "file":
        file_name = "received.jpg"
        file = open(file_name, "wb")

        for frag in whole_msg:
            file.write(frag)
        file.close()
        print("Name: ", file_name, "Size: ", os.path.getsize(file_name), "B")
        print("Path: ", os.path.abspath(file_name))




def switch(socket, server_address):
    while True:
        mode = input("c - client\ns - server\nq - quit")
        if mode == 'c':
            print("Changed role to CLIENT")
            run_client(socket, server_address)
        elif mode == 's':
            print("Changed role to SERVER")
            run_server(socket, server_address)
        elif mode == 'q':
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
        socket.sendto(str.encode("4"), s_addr)
        try:
            data = socket.recv(1500)
        except socket.timeout:
            print("Socket timed out")
        except socket.error as e:
            print(f"Socket error: {e}")
        info = str(data.decode())
        if info == "4":
            print("Staying alive")
        else:
            print("Connection off")
            break
        time.sleep(10)

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


#TODO: chyba na strane serveru, po prenose 1 spravy sa timeoutuje asi alebo neviem, neprijma dalsie spravy a na clientovy vypise timeout
#TODO: switch, keepalive, change header, fix var naming
#switch asi done, server chyba asi done?
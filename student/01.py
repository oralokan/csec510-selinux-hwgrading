#!/usr/bin/env python
import socket
def listen():
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    connection.bind(('0.0.0.0', 80))
    connection.listen(1)
    print("String reversing echo server listening on port 80")
    sock, addr = connection.accept()
    while True:
        data = sock.recv(2048)
        if not data or data == 'bye\n':
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            return
        elif data:
            sock.send(data[::-1][1:] + '\n')

if __name__ == "__main__":
    try:
        listen()
    except KeyboardInterrupt:
        pass

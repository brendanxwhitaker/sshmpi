import time
import socket
import logging
import threading
import socketserver
import multiprocessing as mp
from multiprocessing.connection import Connection


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """ Handles incoming requests. """

    def handle(self):
        """ Actually handle the request. """
        data = str(self.request.recv(1024), "ascii")
        cur_thread = threading.current_thread()
        response = bytes("{}: {}".format(cur_thread.name, data), "ascii")

        # Send the response to the HNP.
        self.server.funnel.send(response)
        logging.info("SERVER: Sent received data through funnel: %s", str(data))


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """ This just adds the ThreadingMixIn. """

    def __init__(self, *args, **kwargs):
        if "funnel" in kwargs:
            self.funnel = kwargs.pop("funnel")
        super().__init__(*args, **kwargs)


def client(ip, port, message):
    """ Dummy client to send test messages to the server. """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(bytes(message, "ascii"))


def listener(funnel: Connection) -> None:
    """ Waits for data and pipes it to HNP via a ThreadedTCPServer. """
    host, port = "127.0.0.1", 8888
    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler, funnel=funnel)
    with server:
        ip, port = server.server_address

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        print("Server loop running in thread:", server_thread.name)

        while 1:
            time.sleep(1)


def main() -> None:
    # Port 0 means to select an arbitrary unused port.
    host, port = "127.0.0.1", 8888
    funnel, spout = mp.Pipe()

    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler, funnel=funnel)
    with server:
        ip, port = server.server_address

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        print("Server loop running in thread:", server_thread.name)

        client(ip, port, "Hello World 1")
        client(ip, port, "Hello World 2")
        client(ip, port, "Hello World 3")

        while 1:
            response = spout.recv()
            print(response)

        server.shutdown()


if __name__ == "__main__":
    main()

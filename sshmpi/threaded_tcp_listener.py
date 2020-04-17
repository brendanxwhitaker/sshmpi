""" TCP server for receiving packets from headspout processes. """
import time
import pickle
import logging
import threading
import socketserver
from multiprocessing.connection import Connection


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """ Handles incoming requests. """

    def handle(self) -> None:
        """ Handles a single request. """
        buf = b""
        while 1:
            # Read the length of the message given in 16 bytes.
            buf += self.request.recv(16)
            t = time.time()

            # Parse the message length bytes.
            blength = buf
            length = int(blength.decode("ascii"))

            # Read the message proper.
            buf = self.request.recv(length + 1)

            # Deserialize the data and send to the backward connection client.
            obj = pickle.loads(buf)
            self.server.funnel.send(obj)  # type: ignore[attr-defined]
            thread = threading.current_thread()
            logging.info(
                "SERVER: %s: Unpickling time: %fs", thread.name, time.time() - t
            )
            logging.info(
                "SERVER: %s: Received %s from remote %f",
                thread.name,
                str(obj),
                time.time(),
            )

            # Reset buffer.
            buf = b""


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """ This just adds the ThreadingMixIn. """
    allow_reuse_address = True

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if "funnel" in kwargs:
            self.funnel = kwargs.pop("funnel")
        super().__init__(*args, **kwargs)


def listener(
    funnel: Connection, kill_spout: Connection, done_funnel: Connection
) -> int:
    """ Waits for data and pipes it to HNP via a ThreadedTCPServer. """
    host, port = "127.0.0.1", 8888
    # pylint: disable=broad-except
    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler, funnel=funnel)
    try:
        with server:
            _ip, port = server.server_address

            # Start a thread with the server -- that thread will then start one
            # more thread for each request
            server_thread = threading.Thread(target=server.serve_forever)
            # Exit the server thread when the main thread terminates
            server_thread.daemon = True
            server_thread.start()
            print("Started server loop in:", server_thread.name)

            signal = kill_spout.recv()
            if signal == "SIGKILL":
                server.shutdown()
                done_funnel.send("DONE")

    except Exception as err:
        server.shutdown()
        raise err

    return 0

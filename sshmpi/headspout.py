#!/usr/bin/env python
""" Called by workers on the head node via SSH. Broadcasts stdout to TCP. """
import sys
import socket
import asyncio
import logging

logging.basicConfig(filename="client-head.log", level=logging.DEBUG)

async def stdin_read():
    """ A version of the above function which explicitly reads the length bytes. """
    ip = "127.0.0.1"
    port = 8888
    logging.info("Attempting to open connection to server.")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        logging.info("Successfully connected to server.")
        buf = b""
        while 1:
            logging.info("Reading from stdin.")
            # Read the length of the message given in 16 bytes.
            buf += sys.stdin.buffer.read(16)

            # Parse the message length bytes.
            blength = buf
            length = int(blength.decode("ascii"))
            logging.info("Decoded length: %d", length)
            sock.sendall(buf)

            # Read the message proper.
            buf = sys.stdin.buffer.read(length + 1)
            sock.sendall(buf)
            logging.info("Message of length %d written to server.", length)

            # Reset buffer.
            buf = b""


def main() -> None:
    """ Reads from stdin and echos bytes to head TCP listener. """
    asyncio.run(stdin_read())


if __name__ == "__main__":
    main()

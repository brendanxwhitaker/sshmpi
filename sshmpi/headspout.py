#!/usr/bin/env python
""" Called by workers on the head node via SSH. Broadcasts stdout to TCP. """
import sys
import asyncio
import logging

BUFFER_SIZE = 1024

logging.basicConfig(filename="client-head.log", level=logging.DEBUG)


async def spout():
    """ Continously reads bytes from stdout and forwards them to SSHMPI HNP. """
    _, writer = await asyncio.open_connection("127.0.0.1", 8888)
    logging.info("Successfully connected to server.")
    try:
        buf = b""
        while 1:
            buf = sys.stdin.buffer.read(BUFFER_SIZE)
            logging.info("Sending: %s" % buf.decode())
            writer.write(buf)

    except KeyboardInterrupt:
        writer.close()
        sys.stdout.flush()


async def stdin_read():
    """ Continously reads bytes from stdout and forwards them to SSHMPI HNP. """
    _, writer = await asyncio.open_connection("127.0.0.1", 8888)
    logging.info("Successfully connected to server.")
    buf = b""
    while 1:
        logging.info("Reading from stdin.")
        sys.stdout.flush()
        # Read the length of the message given in 16 bytes.
        buf += sys.stdin.buffer.read(16)

        # Parse the message length bytes.
        blength = buf
        length = int(blength.decode("ascii"))
        logging.info("Decoded length: %d", length)
        sys.stdout.flush()
        writer.write(buf)

        # Read the message proper.
        buf = sys.stdin.buffer.read(length + 1)
        writer.write(buf)
        logging.info("Message of length %d written to server.", length)

        # Reset buffer.
        buf = b""


def main() -> None:
    """ Reads from stdin and echos bytes to head TCP listener. """
    asyncio.run(stdin_read())


if __name__ == "__main__":
    main()

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


def main() -> None:
    """ Reads from stdin and echos bytes to head TCP listener. """
    asyncio.run(spout())


if __name__ == "__main__":
    main()

#!/usr/bin/env python
""" Called by HNP on remote nodes via SSH. Calls all remote ``Process`` functions. """
import os
import sys
import time
import random
import pickle
import socket
import asyncio
import logging
import argparse
import multiprocessing as mp
from multiprocessing.connection import Connection
from typing import List

from ssh2.channel import Channel  # pylint: disable=no-name-in-module

from pssh.utils import read_openssh_config
from pssh.clients import ParallelSSHClient
from sshmpi.local import get_parcel

logging.basicConfig(filename="remote.log", level=logging.DEBUG)
logging.disable(logging.CRITICAL)

def stdin_read(funnel: Connection) -> None:
    """ Continously reads parcels (length-message) pairs from stdin. """
    buf = b""
    while 1:
        logging.info("Reading from stdin.")
        # Read the length of the message given in 16 bytes.
        buf += sys.stdin.buffer.read(16)

        # Parse the message length bytes.
        blength = buf
        length = int(blength.decode("ascii"))
        logging.info("Decoded length: %d", length)
        sys.stdout.flush()

        # Read the message proper.
        buf = sys.stdin.buffer.read(length + 1)

        # Deserialize the data and send to the backward connection client.
        obj = pickle.loads(buf)
        funnel.send(obj)
        logging.info("Object sent: %s", str(obj))

        # Reset buffer.
        buf = b""


def write_from_pipe(spout: Connection, stream):
    """ Writes from a pipe connection to a stream. """
    while 1:
        data = spout.recv()
        logging.info("Size of packet: %s", str(sys.getsizeof(data)))
        pair = get_parcel(data)

        # Consider buffering the output so we aren't dumping a huge line over SSH.
        stream.write(pair + "\n".encode("ascii"))
        logging.info("Wrote to stream.")
        # await stream.drain()


async def multistream_write_from_pipe(spout: Connection, streams: List[Channel]):
    """ Writes from a pipe connection to a list of SSH streams. """
    while 1:
        data = spout.recv()
        print("Size of packet:", sys.getsizeof(data))
        pair = get_parcel(data)

        # Consider buffering the output so we aren't dumping a huge line over SSH.
        for stream in streams:
            stream.write(pair + "\n".encode("ascii"))


def from_head(funnel: Connection) -> None:
    asyncio.run(stdin_read(funnel))


def to_head(spout: Connection, stream):
    asyncio.run(write_from_pipe(spout, stream))


def multistream_to_head(spout: Connection, streams: list):
    asyncio.run(multistream_write_from_pipe(spout, streams))


def target(in_spout: Connection, out_funnel: Connection) -> None:
    """ Dummy loop just forwards all bytes back to the head node. """
    while 1:
        data = in_spout.recv()
        logging.info("Received data from in_spout: %s", str(data))
        if isinstance(data, str):
            local = socket.gethostname()
            data = "%s: %s" % (local, data)
        out_funnel.send(data)


def main() -> None:
    """ Makes a backward connection to head node and reads from stdin. """
    # Parse arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", type=str)
    parser.add_argument("--rank", type=int)
    args = parser.parse_args()
    print("Hostname:", args.hostname)
    print("Rank:", args.rank)

    in_funnel, in_spout = mp.Pipe()

    # Instantiate connection back to the head node.
    if args.hostname:
        pkey = os.path.expanduser("~/.ssh/id_rsa")
        _, _, port, _ = read_openssh_config(args.hostname)
        logging.info("Sleeping: %ds", args.rank)
        time.sleep(args.rank)
        logging.info("Instantiating client.")
        client = ParallelSSHClient([args.hostname], port=port, pkey=pkey)
        output = client.run_command("headspout")

        # TODO: Figure out the type of this.
        stdin = output[args.hostname].stdin

        out_funnel, out_spout = mp.Pipe()
        p_out = mp.Process(target=write_from_pipe, args=(out_spout, stdin))
        p_out.start()

        # This will run the user's code.
        p_target = mp.Process(target=target, args=(in_spout, out_funnel))
        p_target.start()

    stdin_read(in_funnel)


if __name__ == "__main__":
    main()

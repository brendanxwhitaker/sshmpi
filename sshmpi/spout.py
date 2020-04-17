#!/usr/bin/env python
""" Called by HNP on remote nodes via SSH. Calls all remote ``Process`` functions. """
import sys
import pickle
import asyncio
import argparse
import multiprocessing as mp
from multiprocessing.connection import Connection
from typing import List

from pssh.utils import read_openssh_config
from pssh.clients import ParallelSSHClient
from ssh2.channel import Channel
from sshmpi.local import get_parcel


async def stdin_read(funnel: Connection) -> None:
    """ Continously reads parcels (length-message) pairs from stdin. """
    try:
        buf = b""
        while 1:
            # Read the length of the message given in 16 bytes.
            buf += sys.stdin.buffer.read(16)
            blength = buf
            length = int(blength.decode("ascii"))
            print("Decoded length:", length)

            # Read the message proper.
            buf = sys.stdin.buffer.read(length + 1)

            # Deserialize the data and send to the backward connection client.
            obj = pickle.loads(buf)
            funnel.send(obj)

            # Reset buffer.
            buf = b""
    except KeyboardInterrupt:
        sys.stdout.flush()


async def write_from_pipe(spout: Connection, stream):
    """ Writes from a pipe connection to a stream. """
    while 1:
        data = spout.recv()
        print("Size of packet:", sys.getsizeof(data))
        pair = get_parcel(data)

        # Consider buffering the output so we aren't dumping a huge line over SSH.
        stream.write(pair + "\n".encode("ascii"))
        await stream.drain()


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


def main() -> None:
    """ Makes a backward connection to head node and reads from stdin. """
    # Parse arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", type=str)
    args = parser.parse_args()

    in_funnel, in_spout = mp.Pipe()
    p_in = mp.Process(target=from_head, args=(in_funnel,))

    # Instantiate connection back to the head node.
    if args.hostname:
        pkey = ".ssh/id_rsa"
        _, _, port, _ = read_openssh_config(args.hostname)
        client = ParallelSSHClient([args.hostname], port=port, pkey=pkey)
        output = client.run_command("./headspout")

        # TODO: Figure out the type of this.
        stdin = output[args.hostname].stdin

        out_funnel, out_spout = mp.Pipe()
        p_out = mp.Process(target=to_head, args=(out_spout, stdin))
        p_out.start()

    p_in.start()

    # Dummy loop just forwards all bytes back to the head node.
    while 1:
        data = in_spout.recv()
        out_funnel.send(data)


if __name__ == "__main__":
    main()

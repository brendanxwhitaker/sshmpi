""" Called by HNP on remote nodes via SSH. Calls all remote ``Process`` functions. """
import sys
import pickle
import asyncio
import argparse
from pssh.clients import ParallelSSHClient
from pssh.utils import read_openssh_config
from sshmpi.local import write


async def spout():
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
            arr = pickle.loads(buf)
            print(arr)
            sys.stdout.write("Hello!!\n")
            sys.stdout.flush()
            buf = b""
    except KeyboardInterrupt:
        sys.stdout.flush()


def main() -> None:
    """ Makes a backward connection to head node and reads from stdin. """
    # Parse arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", type=str)
    args = parser.parse_args()

    # Instantiate parallel SSH connections.
    if args.hostname:
        pkey = ".ssh/id_rsa"
        _, _, port, _ = read_openssh_config(args.hostname)
        client = ParallelSSHClient([args.hostname], port=port, pkey=pkey)
        output = client.run_command("./headspout")
        stdin = output[args.hostname].stdin
        asyncio.run(write(stdin))

    asyncio.run(spout())


if __name__ == "__main__":
    main()

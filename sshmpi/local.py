""" Proof-of-concept for async subprocess byte streams. """
import sys
import pickle
import asyncio
import numpy as np


async def write(stdin):
    """ Sample writes to a stream. """
    for _ in range(10):
        arr = np.random.rand(10)
        print("Size of array:", sys.getsizeof(arr))
        pair = get_parcel(arr)

        # Consider buffering the output so we aren't dumping a huge line over SSH.
        stdin.write(pair + "\n".encode("ascii"))
        await stdin.drain()


async def read(stdout):
    """ Sample reading from a stream. """
    bnewline = "\n".encode("ascii")
    buf = b""
    while 1:
        buf += await stdout.read(1)
        if buf.endswith(bnewline):
            print("OUT:", buf.decode("ascii"), end="")
            buf = b""
        await asyncio.sleep(0.0001)


async def err(stderr):
    """ Display stderr from stream after termination. """
    while 1:
        buf = await stderr.read()
        if buf:
            print("ERR:", buf.decode("ascii"))
        await asyncio.sleep(0.5)


def get_parcel(obj: object) -> bytes:
    """ Pickles an object and returns bytes of a length+message pair. """
    message = pickle.dumps(obj)

    # Get representation of then length of ``message`` in bytes.
    length = str(len(message)).encode("ascii")
    assert len(length) <= 16

    # Compute the pad so that prefix is a 16-byte sequence.
    padsize = 16 - len(length)
    pad = ("0" * padsize).encode("ascii")

    # Concatenate prefix and message.
    parcel = pad + length + message

    return parcel


async def run():
    """ Run the example. """
    p = await asyncio.create_subprocess_shell(
        "python3 spout.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await asyncio.gather(write(p.stdin), read(p.stdout), err(p.stderr))


if __name__ == "__main__":
    asyncio.run(run())

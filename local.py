import sys
import pickle
import asyncio
import numpy as np


async def write(stdin):
    for _ in range(10):
        arr = np.random.rand(10)
        print("Size of array:", sys.getsizeof(arr))
        message = pickle.dumps(arr)
        pair = get_length_bytes(message) + message

        # Consider buffering the output so we aren't dumping a huge line over SSH.
        stdin.write(pair + "\n".encode("ascii"))
        await stdin.drain()


async def read(stdout):
    nl = "\n".encode("ascii")
    buf = b""
    while 1:
        buf += await stdout.read(1)
        if buf.endswith(nl):
            print("OUT:", buf.decode("ascii"), end="")
            buf = b""
        await asyncio.sleep(0.0001)

async def err(stderr):
    while 1:
        buf = await stderr.read()
        if buf:
            print("ERR:", buf.decode("ascii"))
        await asyncio.sleep(0.5)


def get_length_bytes(message: bytes) -> bytes:
    """ Gets a bytes representation of the length of ``message`` in bytes. """
    length = str(len(message)).encode("ascii")
    assert len(length) <= 16
    padsize = 16 - len(length)
    pad = ("0" * padsize).encode("ascii")
    return pad + length


async def run():
    p = await asyncio.create_subprocess_shell(
        "python3 spout.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await asyncio.gather(write(p.stdin), read(p.stdout), err(p.stderr))

if __name__ == "__main__":
    asyncio.run(run())

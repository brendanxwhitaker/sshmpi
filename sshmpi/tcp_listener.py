""" A simple TCP server listener. """
import sys
import pickle
import asyncio
import logging
import functools
import multiprocessing as mp
from multiprocessing.connection import Connection

logging.basicConfig(filename="server-head.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


async def handle_echo(reader, writer, funnel):
    """ Echoes any data sent to the server back to the sender. """
    while 1:
        logging.info("Waiting for 10 bytes.")
        data = await reader.read(10)
        logging.info("Received 10 bytes.")
        message = data.decode()
        addr = writer.get_extra_info("peername")
        logging.info(f"Received {message!r} from {addr!r}")

        funnel.send(message)
        logging.info("Sent message into head funnel: %s", message)


async def stream_read(reader, writer, funnel):
    buf = b""
    while 1:
        # Read the length of the message given in 16 bytes.
        buf += reader.read(16)

        # Parse the message length bytes.
        blength = buf
        length = int(blength.decode("ascii"))
        logging.info("SERVER: Decoded length: %s" % length)
        sys.stdout.flush()

        # Read the message proper.
        buf = reader.read(length + 1)

        # Deserialize the data and send to the backward connection client.
        obj = pickle.loads(buf)
        funnel.send(obj)
        logging.info("SERVER: Object sent: %s" % str(obj))

        # Reset buffer.
        buf = b""


async def wait_for_data(funnel: Connection):
    """ Runs a persistent server. """
    callback = functools.partial(stream_read, funnel=funnel)
    server = await asyncio.start_server(callback, "127.0.0.1", 8888)

    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    async with server:
        await server.serve_forever()


async def dummy_spout():
    """ Sends dummy data to SSHMPI HNP through the async listener. """
    _, writer = await asyncio.open_connection("127.0.0.1", 8888)
    for _ in range(10):
        writer.write("abc".encode())
    writer.close()


def produce():
    asyncio.run(dummy_spout())


def listener(funnel: Connection) -> None:
    """ Asynchronously waits for data and pipes it to HNP. """
    asyncio.run(wait_for_data(funnel))


def main() -> None:
    funnel, spout = mp.Pipe()
    consumer = mp.Process(target=listener, args=(funnel,))
    producer = mp.Process(target=produce)
    consumer.start()
    producer.start()
    data = spout.recv()
    print("Data retrieved:", data)


if __name__ == "__main__":
    main()

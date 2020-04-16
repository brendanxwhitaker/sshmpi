""" A simple TCP server listener. """
import asyncio
import functools
import multiprocessing as mp
from multiprocessing.connection import Connection


async def handle_echo(reader, writer, funnel):
    """ Echoes any data sent to the server back to the sender. """
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info("peername")

    print(f"Received {message!r} from {addr!r}")

    print(f"Send: {message!r}")
    funnel.send(message)
    writer.write(data)
    await writer.drain()

    print("Close the connection")
    writer.close()


async def wait_for_data(funnel: Connection):
    """ Runs a persistent server. """
    callback = functools.partial(handle_echo, funnel=funnel)
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

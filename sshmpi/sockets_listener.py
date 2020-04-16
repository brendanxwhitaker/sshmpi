import socket
import asyncio
import multiprocessing as mp
from multiprocessing.connection import Connection


async def wait_for_data(rsock, wsock, funnel):
    # Get a reference to the current event loop because
    # we want to access low-level APIs.
    loop = asyncio.get_running_loop()

    # Register the open socket to wait for data.
    reader, writer = await asyncio.open_connection(sock=rsock)

    # Simulate the reception of data from the network
    loop.call_soon(wsock.send, "abc".encode())

    # Wait for data
    data = await reader.read(100)

    # Got data, we are done: close the socket
    print("Received:", data.decode())
    funnel.send(data)
    writer.close()

    # Close the second socket
    wsock.close()


def listener(funnel: Connection) -> None:
    """ Asynchronously waits for data and pipes it to HNP. """
    # Create a pair of connected sockets.
    rsock, wsock = socket.socketpair()
    asyncio.run(wait_for_data(rsock, wsock, funnel))


def main():
    funnel, spout = mp.Pipe()
    p = mp.Process(target=listener, args=(funnel,))
    p.start()
    data = spout.recv()
    print("Data retrieved:", data)


if __name__ == "__main__":
    main()

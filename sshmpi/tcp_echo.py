""" Example of a TCP echo function to connect to running server. """
import asyncio


async def tcp_echo_client(message):
    """ Sends a message to a server. """
    _, writer = await asyncio.open_connection("127.0.0.1", 8888)
    print("Sending: %s" % message)
    writer.write(message.encode())
    writer.close()


asyncio.run(tcp_echo_client("Hello World!"))

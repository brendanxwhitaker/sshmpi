import asyncio

async def tcp_echo_client(message):
    reader, writer = await asyncio.open_connection("127.0.0.1", 8888)
    print("Sending: %s" % message)
    writer.write(message.encode())

asyncio.run(tcp_echo_client("Hello World!"))

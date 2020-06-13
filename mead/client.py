#!/usr/bin/env python
# coding:utf-8
""" Start a UDP NAT traversal client. """
import sys
import time
import socket
import logging
from typing import Tuple, Callable
from threading import Thread

import multiprocessing as mp
from multiprocessing.connection import Connection

from mead.utils import bytes2addr, get_length_message_pair

# pylint: disable=invalid-name

FullCone = "Full Cone"  # 0
RestrictNAT = "Restrict NAT"  # 1
RestrictPortNAT = "Restrict Port NAT"  # 2
SymmetricNAT = "Symmetric NAT"  # 3
UnknownNAT = "Unknown NAT"  # 4
NATTYPE = (FullCone, RestrictNAT, RestrictPortNAT, SymmetricNAT, UnknownNAT)


class Client:
    """ The UDP client for interacting with the server and other Clients. """

    def __init__(
        self,
        server_ip: str,
        port: int,
        channel: str,
        in_funnel: Connection,
        out_queue: mp.Queue,
    ) -> None:
        self.master = (server_ip, port)
        self.channel = channel
        self.sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Counters for packet ordering.
        self.out_idx = 0
        self.in_idx = 0

        # Heaps containing ``(idx, msg)``.
        self.in_heap: List[Tuple[int, bytes]] = []
        self.out_heap: List[Tuple[int, bytes]] = []

        # If testing with server and both clients on localhost, use ``127.0.0.1``.
        self.target: Tuple[str, int] = ("", 0)
        self.peer_nat_type = ""

        self.in_funnel = in_funnel
        self.out_queue = out_queue

    def request_for_connection(self, nat_type_id: str = "0") -> None:
        """ Send a request to the server for a connection. """
        # Create a socket.
        self.sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Send channel and NAT type to server, requesting a connection.
        msg = (self.channel + " %s" % nat_type_id).encode("ascii")
        self.sockfd.sendto(msg, self.master)

        # Wait for ``ok``, acknowledgement of request.
        data, _ = self.sockfd.recvfrom(len(self.channel) + 3)
        if data.decode("ascii") != "ok " + self.channel:
            print("unable to request!")
            sys.exit(1)

        # Confirm we've received the ``ok``, tell server to connect us to channel.
        self.sockfd.sendto("ok".encode("ascii"), self.master)

        # Wait for a partner.
        print("request sent, waiting for partner in channel '%s'..." % self.channel)
        data, _ = self.sockfd.recvfrom(8)

        # Decode the partner's address and NAT type.
        self.target, peer_nat_type_id = bytes2addr(data)
        print((self.target, peer_nat_type_id))
        self.peer_nat_type = NATTYPE[peer_nat_type_id]

        # Get target address and port.
        addr, port = self.target
        print("connected to %s:%s with NAT type: %s" % (addr, port, self.peer_nat_type))

    def recvloop(self, sock: socket.socket) -> None:
        """ Receive message callback. """
        while True:
            # Receive 16 bytes (size of length prefix).
            bdata, addr = sock.recvfrom(16)
            data = bdata.decode("ascii")
            logging.info("%s: %s", self.channel, data)

            # If the data is from a valid sender.
            if addr in (self.target, self.master):

                # Handle timeout refresh tokens.
                if data == "refresh":
                    sock.sendto("confirm".encode(), self.target)
                if data == "confirm":
                    continue

                # Parse the message length bytes.
                if not data.isnumeric():
                    continue
                length = int(data)

                logging.info("%s: length: %d", self.channel, length)

                # Receive the object.
                bdata, addr = sock.recvfrom(length)

                # Abort if the sender changed.
                if addr not in (self.target, self.master):
                    logging.info("%s: sender address changed.", self.channel)
                    continue

                self.in_funnel.send(bdata)

    def sendloop(self, sock: socket.socket) -> None:
        """ Send message callback. """
        while True:
            obj = self.out_queue.get()

            # Serialize in bytes as a length-message pair.
            pair: bytes = get_length_message_pair(obj)

            logging.info("%s: sending pair: %s", self.channel, str(obj))

            # Send to target client.
            sock.sendto(pair[:16], self.target)
            sock.sendto(pair[16:], self.target)

    def send(self, msg: bytes) -> None:
        """ Atomic send with ACK and in-order delivery. """
        prefix = self.out_idx.to_bytes(4, byteorder="big", signed=False)
        self.sockfd.sendto(prefix + msg, self.target)

    def recv(self, n: int) -> bytes:
        """ Atomic recv with ACK and in-order delivery. """
        while 1:
            # See if the requested packet is in the heap.
            if self.in_heap[0][0] == self.in_idx + 1:
                in_idx, msg = heappop(self.in_heap)
                self.in_idx += 1
                break

            # Read from the socket.
            raw, addr = self.sockfd.recvfrom(4 + n)
            if addr != self.target:
                continue

            # Order the messages.
            prefix, msg = raw[:4], raw[4:]
            in_idx = int.from_bytes(prefix, byteorder="big", signed=False)

            # If the packet has the right index, return it.
            if in_idx == self.in_idx + 1:
                self.in_idx += 1
                break

            # If its index is too big, store it for later.
            elif in_idx > self.in_idx + 1:
                heappush(in_heap, (in_idx, msg))

            # Otherwise, throw it out.
            else:
                print("Received packet %d again." % in_idx)

        return msg

    @staticmethod
    def chat_fullcone(
        send: Callable[[socket.socket], None],
        recv: Callable[[socket.socket], None],
        sock: socket.socket,
    ) -> None:
        """ Start the send and recv threads. """
        ts = Thread(target=send, args=(sock,))
        ts.setDaemon(True)
        ts.start()
        tr = Thread(target=recv, args=(sock,))
        tr.setDaemon(True)
        tr.start()

    def main(self) -> None:
        """ Start a chat session. """
        # Connect to the server and request a channel.
        self.request_for_connection(nat_type_id="0")

        # Initialize the connection.
        for _ in range(3):
            self.sockfd.sendto("refresh".encode(), self.target)
            time.sleep(1)
        data = self.sockfd.recvfrom(1024)[0].decode()
        if data == "refresh":
            self.sockfd.sendto("confirm".encode(), self.target)

        # Chat with peer.
        print("FullCone chat mode")
        self.chat_fullcone(self.sendloop, self.recvloop, self.sockfd)

        # Let the threads run.
        while 1:
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("exit")
                sys.exit()

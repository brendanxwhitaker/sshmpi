#!/usr/bin/env python
# coding:utf-8
""" Start a UDP NAT traversal client. """
import sys
import time
import socket
import struct
import logging
from typing import Tuple, Callable, Dict, List, Any
from threading import Thread

import multiprocessing as mp
from multiprocessing.connection import Connection

import dill

from mead.classes import (
    _Process,
    _Funnel,
    _Spout,
    _Join,
    inject,
    extract,
)
from mead.translation import get_length_message_pair

logging.basicConfig(filename="mead.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

# pylint: disable=invalid-name

FullCone = "Full Cone"  # 0
RestrictNAT = "Restrict NAT"  # 1
RestrictPortNAT = "Restrict Port NAT"  # 2
SymmetricNAT = "Symmetric NAT"  # 3
UnknownNAT = "Unknown NAT"  # 4
NATTYPE = (FullCone, RestrictNAT, RestrictPortNAT, SymmetricNAT, UnknownNAT)


def reset(server_ip: str, port: int) -> int:
    """ Resets the channel map of the server. """
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send channel and NAT type to server, requesting a connection.
    master = (server_ip, port)
    breset = "RESET".encode("ascii")
    sockfd.sendto(breset, master)

    # Wait for ``ok``, acknowledgement of request.
    bdata, _ = sockfd.recvfrom(1024)
    data = bdata.decode()
    if data == "RESET_COMPLETE":
        return 0
    return 1


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
        msg = (self.channel + " {0}".format(nat_type_id)).encode("ascii")
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

    def recv_msg(self, sock: socket.socket) -> None:
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
                    logging.info("DEBUG: received refresh token.")
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

    def send_msg(self, sock: socket.socket) -> None:
        """ Send message callback. """
        while True:
            obj = self.out_queue.get()

            # Serialize in bytes as a length-message pair.
            pair: bytes = get_length_message_pair(obj)

            logging.info("%s: sending pair: %s", self.channel, str(obj))

            # Send to target client.
            sock.sendto(pair[:16], self.target)
            sock.sendto(pair[16:], self.target)

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

        # Send a refresh token to initialize the connection.
        data = "refresh"
        bdata = data.encode("ascii")
        self.sockfd.sendto(bdata, self.target)

        # Wait for a refresh token from the other client.
        bdata, _addr = self.sockfd.recvfrom(1024)
        data = bdata.decode("ascii")
        assert data == "refresh"

        # Chat with peer.
        print("FullCone chat mode")
        self.chat_fullcone(self.send_msg, self.recv_msg, self.sockfd)

        # Let the threads run.
        while 1:
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("exit")
                sys.exit()


def bytes2addr(bytes_address: bytes) -> Tuple[Tuple[str, int], int]:
    """Convert a hash to an address pair."""
    if len(bytes_address) != 8:
        raise ValueError("invalid bytes_address")
    host = socket.inet_ntoa(bytes_address[:4])

    # Unpack returns a tuple even if it contains exactly one item.
    port = struct.unpack("H", bytes_address[-4:-2])[0]
    nat_type_id = struct.unpack("H", bytes_address[-2:])[0]
    target = (host, port)
    return target, nat_type_id


def remote(server_ip: str, port: int, channel: str) -> None:
    """ Runs the client for a remote worker. """
    # The ``in_spout`` receives data coming from the head node.
    in_funnel, in_spout = mp.Pipe()

    # The ``out_queue`` sends data going to the head node.
    out_queue: mp.Queue = mp.Queue()

    # For fo
    aux_funnel, aux_spout = mp.Pipe()

    # Create and start the client.
    c = Client(server_ip, port, channel, in_funnel, out_queue)
    p_client = mp.Process(target=c.main)
    p_client.start()

    # We'll first write this file so it only handles one Process, and then add
    # an abstraction for multiple later on.

    # Wait until we get an instruction to start a mead.Process.
    while 1:
        logging.info("REMOTE: waiting on inspout.")

        # Assume obj is already unpickled.
        bprocess = in_spout.recv()
        obj = dill.loads(bprocess)

        logging.info("REMOTE: received obj: %s", obj)
        if not isinstance(obj, _Process):
            logging.info("ERR: obj not _Process: %s", obj)

        # If we're sent a mead process to run.
        if isinstance(obj, _Process):
            p = obj

            # Create pipes to communicate with injection/extraction processes.
            injection_funnels: Dict[str, Connection] = {}
            extraction_spouts: Dict[str, Connection] = {}

            # Iterate over the arguments, replacing mead pipes with mp pipes.
            mp_args: List[Any] = []
            for arg in p.args:
                if isinstance(arg, _Funnel):
                    funnel, spout = mp.Pipe()
                    extraction_spouts[arg.pipe_id] = spout
                    mp_args.append(funnel)
                    del funnel
                    del spout
                elif isinstance(arg, _Spout):
                    funnel, spout = mp.Pipe()
                    logging.info(
                        "REMOTE: adding injection funnel with pipe id: %s", arg.pipe_id
                    )
                    logging.info("REMOTE: adding spout to mp args: %s", str(spout))
                    injection_funnels[arg.pipe_id] = funnel
                    mp_args.append(spout)
                    del funnel
                    del spout
                else:
                    mp_args.append(arg)

            # Iterate over the keyword arguments, replacing mead pipes with mp pipes.
            mp_kwargs: Dict[str, Any] = {}
            for name, arg in p.kwargs.items():
                if isinstance(arg, _Funnel):
                    funnel, spout = mp.Pipe()
                    extraction_spouts[arg.pipe_id] = spout
                    mp_kwargs[name] = funnel
                elif isinstance(arg, _Spout):
                    funnel, spout = mp.Pipe()
                    injection_funnels[arg.pipe_id] = funnel
                    mp_kwargs[name] = spout
                else:
                    mp_kwargs[name] = arg

            logging.info("REMOTE: starting user processes.")
            logging.info("REMOTE: injection funnels: %s:", str(injection_funnels))
            logging.info("REMOTE: mpargs: %s:", str(mp_args))

            p_user = mp.Process(target=p.target, args=tuple(mp_args), kwargs=mp_kwargs)
            p_user.start()

            # Create and start the injection process.
            p_inject = mp.Process(
                target=inject, args=(in_spout, injection_funnels, aux_funnel)
            )
            p_inject.start()

            # Create and start the extraction processes.
            extraction_processes: Dict[str, mp.Process] = {}
            for pipe_id, extraction_spout in extraction_spouts.items():
                p_extract = mp.Process(
                    target=extract, args=(pipe_id, out_queue, extraction_spout)
                )
                p_extract.start()
                extraction_processes[pipe_id] = p_extract

            logging.info("REMOTE: break.")
            break

    while 1:
        obj = aux_spout.recv()
        if isinstance(obj, _Join):
            logging.info("REMOTE: joining.")
            logging.info("REMOTE: sending reply.")
            out_queue.put(obj)
            p_user.join()

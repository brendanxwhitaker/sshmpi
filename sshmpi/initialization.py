""" Functions for initializing client connections. """
import os
import time
import socket
import logging
from typing import List, Dict, Tuple

import multiprocessing as mp
from multiprocessing.connection import Connection

from pssh.utils import read_openssh_config
from pssh.clients import ParallelSSHClient
from sshmpi.spout import multistream_to_head
from sshmpi.openssh import get_available_hostnames_from_sshconfig

from sshmpi.threaded_tcp_listener import listener


# TODO: Use this instead of SSH config to make setup more explicit.
def get_nodes() -> List[str]:
    """ Read hostnames of remote nodes. """
    nodes_path = os.path.expanduser("~/nodes.json")
    with open(nodes_path, "r") as nodes_file:
        lines = nodes_file.read().split("\n")
        print(lines)
    return lines


def test_connections(hosts: List[str]) -> None:
    """ Test connections to all hosts. """
    latency_map: Dict[str, float] = {}
    for host in hosts:
        mean_latency = test_single_connection(host, 10)
        latency_map[host] = mean_latency
    latency_items = sorted(latency_map.items(), key=lambda x: x[1])
    for host, latency in latency_items:
        print("%s latency: %f" % (host, latency))


def test_single_connection(host: str, k: int) -> float:
    """ Test the latency to a single node from localhost. """
    hosts = [host]

    # Open the connection.
    p_in, p_out, out_funnel, in_spout, kill_funnel = open_connection(hosts)

    # Initialize variables.
    j = 0
    i = 0
    t = time.time()

    # Aggregate latencies.
    latencies: List[float] = []

    # Send packets through roundtrip ``k`` times.
    while i < k:

        if j == 0:

            # Record latency.
            if i > 0:
                latency = time.time() - t
                latencies.append(latency)
                print("Finished round %d in %fs" % (i, latency))
                t = time.time()

            # Send a packet.
            data = "Packet |%d|" % i
            out_funnel.send("Packet |%d|" % i)
            logging.info("Sent packet through first pipe at %f", time.time())

        # Receive a packet.
        reply = in_spout.recv()
        logging.info("RETURN: Received reply %s at %f", str(reply), time.time())
        if data in reply:
            j = (j + 1) % len(hosts)
            if j == 0:
                i += 1

    # Compute mean latency and kill the server.
    mean = sum(latencies) / len(latencies)
    kill_funnel.send("SIGKILL")

    # Kill the associated processes.
    p_in.terminate()
    p_in.join()
    p_out.terminate()
    p_out.join()

    return mean


def open_connection(
    hosts: List[str],
) -> Tuple[mp.Process, mp.Process, Connection, Connection, Connection]:
    """ Open a connection to the remote workers in ``hosts``. """
    print("Hosts:", hosts)

    # Get private key.
    pkey = os.path.expanduser("~/.ssh/id_rsa")

    # Per-host config dictionaries.
    config = {}
    for hostname in hosts:
        _, _, port, _ = read_openssh_config(hostname)
        config[hostname] = {"port": port}

    # Start the client.
    init_delay = 2
    localhost = socket.gethostname()
    client = ParallelSSHClient(hosts, host_config=config, pkey=pkey)
    host_args = [(localhost, (i + 1) * init_delay) for i in range(len(hosts))]
    output = client.run_command("spout --hostname %s --rank %d", host_args=host_args)
    stdins = [out.stdin for out in output.values()]

    # Bytes coming out of ``in_spout`` are from a remote host.
    in_funnel, in_spout = mp.Pipe()
    out_funnel, out_spout = mp.Pipe()
    kill_funnel, kill_spout = mp.Pipe()

    # The listener will dump bytes sent to ``127.0.0.1:8888`` into the funnel.
    p_in = mp.Process(target=listener, args=(in_funnel, kill_spout))
    p_in.start()

    # Start a process to send bytes to remote workers.
    p_out = mp.Process(target=multistream_to_head, args=(out_spout, stdins))
    p_out.start()

    sentinel = "Initialized."
    out_funnel.send(sentinel)
    reply = in_spout.recv()
    print(reply)
    assert sentinel in reply

    return p_in, p_out, out_funnel, in_spout, kill_funnel


def init() -> None:
    """ Public-facing API for SSHMPI initialization. """
    hosts = get_available_hostnames_from_sshconfig()
    test_connections(hosts)

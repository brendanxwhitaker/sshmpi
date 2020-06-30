""" Functions for initializing client connections. """
import os
import json
import socket
import multiprocessing as mp
from typing import Dict, Mapping

import stun
from pssh.utils import read_openssh_config
from pssh.clients import ParallelSSHClient

from mead import cellar
from mead.utils import get_available_hostnames_from_sshconfig
from mead.client import Client


def init(config_path: str = "~/config.json") -> None:
    """ Public-facing API for SSHMPI initialization. """
    with open(os.path.expanduser(config_path), "r") as config_file:
        config = json.load(config_file)
        server_ip = config["server_ip"]
        port = config["port"]
        hosts = config.get("hostnames", [])

    # Per-host config dictionaries.
    host_config = {}

    # Get hostnames of remote nodes.
    if not hosts:
        hosts = get_available_hostnames_from_sshconfig()
        for hostname in hosts:
            _, _, remote_port, _ = read_openssh_config(hostname)
            host_config[hostname] = {"port": remote_port}
    else:
        for hostname in hosts:
            host_config[hostname] = {}

    cellar.HOSTNAMES = hosts
    print("Hosts:", hosts)

    # Get private key.
    pkey = os.path.expanduser("~/.ssh/id_rsa")

    # Start the ssh client.
    sshclient = ParallelSSHClient(hosts, host_config=host_config, pkey=pkey)

    # Reserve local UDP ports for each remote node.
    # TODO: Address possibility that ports are already in-use by another program.
    # HARDCODE
    i = 50000
    head_ip = ""
    ports: Mapping[str, int] = {}
    for name in hosts:
        _, external_ip, external_port = stun.get_ip_info(source_port=i)
        head_ip = external_ip
        ports[name] = external_port
        i += 1

    # NOTE: We're not using the rendezvous server anymore.
    # Reset the channel map of the rendezvous server.
    # reset(server_ip, port)

    # Command string format arguments are in ``host_args``.
    host_args = [(head_ip, ports[name], name) for name in hosts]
    sshclient.run_command(
        "meadclient %s %s %s > mead_global.log 2>&1",
        host_args=host_args,
        shell="bash -ic",
    )

    # Create and start the head node client (one for each remote node).
    head_processes: Dict[str, mp.Process] = {}
    for hostname in hosts:

        # The ``in_spout`` receives data coming from the remote node.
        in_funnel, in_spout = mp.Pipe()
        cellar.HEAD_SPOUTS[hostname] = in_spout

        # The ``out_queue`` sends data going to the remote node.
        out_queue: mp.Queue = mp.Queue()
        cellar.HEAD_QUEUES[hostname] = out_queue

        # We use the hostname as the channel.
        leader = Client(server_ip, port, hostname, in_funnel, out_queue)
        p_client = mp.Process(target=leader.main)
        p_client.start()

        head_processes[hostname] = p_client

    # Store references to the head processes and SSH client.
    cellar.HEAD_PROCESSES = head_processes
    cellar.SSHCLIENT = sshclient


def kill() -> None:
    """ Kills head processes amd remote meadclient processes. """
    for p in cellar.HEAD_PROCESSES.values():
        p.terminate()
        p.join()
    output = cellar.SSHCLIENT.run_command("pkill -e meadclient")
    for _, out in output.items():
        for line in out.stdout:
            print(line)


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

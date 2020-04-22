""" Functions for initializing client connections. """
import os
import json
import socket
from typing import List, Dict

import multiprocessing as mp

from pssh.utils import read_openssh_config
from pssh.clients import ParallelSSHClient

from mead import cellar
from mead.client import Client
from mead.openssh import get_available_hostnames_from_sshconfig


# TODO: Use this instead of SSH config to make setup more explicit.
def get_nodes() -> List[str]:
    """ Read hostnames of remote nodes. """
    nodes_path = os.path.expanduser("~/nodes.json")
    with open(nodes_path, "r") as nodes_file:
        lines = nodes_file.read().split("\n")
        print(lines)
    return lines


def init() -> None:
    """ Public-facing API for SSHMPI initialization. """
    # Get hostnames of remote nodes.
    hosts = get_available_hostnames_from_sshconfig()
    cellar.HOSTNAMES = hosts
    print("Hosts:", hosts)

    # Get private key.
    pkey = os.path.expanduser("~/.ssh/id_rsa")

    # Get server hostname.
    # TODO: User should have to pass in the config path through ``init()`` instead.
    config_path = os.path.expanduser("~/config.json")
    if not os.path.isfile(config_path):
        raise ValueError("Config file not found at: %s" % config_path)
    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    # Per-host config dictionaries.
    host_config = {}
    for hostname in hosts:
        _, _, port, _ = read_openssh_config(hostname)
        host_config[hostname] = {"port": port}

    # Start the ssh client.
    init_delay = 2
    localhost = socket.gethostname()
    sshclient = ParallelSSHClient(hosts, host_config=host_config, pkey=pkey)

    # Command string format arguments are in ``host_args``.
    host_args = [(config["server_ip"], config["port"], hostname) for hostname in hosts]
    # output = sshclient.run_command("meadclient %s %s %s", host_args=host_args)

    # Create and start the head node clients.
    head_processes: Dict[str, mp.Process] = {}
    for hostname in hosts:

        # The ``in_spout`` receives data coming from the remote node.
        in_funnel, in_spout = mp.Pipe()
        cellar.HEAD_SPOUTS[hostname] = in_spout

        # TODO: Consider overriding getattr on ``cellar`` to tell the user they
        # need to run ``mead.init()`` first if they try to start a
        # ``mead.Process``.

        # The ``out_queue`` sends data going to the remote node.
        out_queue: mp.Queue = mp.Queue()
        cellar.HEAD_QUEUES[hostname] = out_queue

        # Get connection information from ``config``.
        # TODO: Don't use ``port`` for two different things.
        server_ip: str = config["server_ip"]
        port = config["port"]

        # We use the hostname as the channel.
        leader = Client(server_ip, port, hostname, in_funnel, out_queue)
        p_client = mp.Process(target=leader.main)
        p_client.start()

        head_processes[hostname] = p_client

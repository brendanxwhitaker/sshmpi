""" Functions for initializing client connections. """
import os
import json
from typing import Dict

import multiprocessing as mp

from pssh.utils import read_openssh_config
from pssh.clients import ParallelSSHClient

from mead import cellar
from mead.client import Client
from mead.openssh import get_available_hostnames_from_sshconfig


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

    # Command string format arguments are in ``host_args``.
    host_args = [(server_ip, port, hostname) for hostname in hosts]
    output = sshclient.run_command("meadclient %s %s %s", host_args=host_args)

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

        # We use the hostname as the channel.
        leader = Client(server_ip, port, hostname, in_funnel, out_queue)
        p_client = mp.Process(target=leader.main)
        p_client.start()

        head_processes[hostname] = p_client

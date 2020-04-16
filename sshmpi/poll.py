""" Functions for initializing client connections. """
import os
import time
import multiprocessing as mp
from typing import List

from pssh.clients import ParallelSSHClient
from pssh.utils import read_openssh_config
from sshmpi.tcp_listener import listener
from sshmpi.utils import get_available_hostnames_from_sshconfig


# TODO: Use this instead of SSH config to make setup more explicit.
def get_nodes() -> List[str]:
    """ Read hostnames of remote nodes. """
    nodes_path = os.path.expanduser("~/nodes.json")
    with open(nodes_path, "r") as nodes_file:
        lines = nodes_file.read().split("\n")
        print(lines)
    return lines


def init():
    """ Public-facing API for SSHMPI initialization. """
    # Define private key path and hostnames.
    pkey = os.path.expanduser("~/.ssh/id_rsa")

    hosts = get_available_hostnames_from_sshconfig()
    print("Hosts:", hosts)

    # Per-host config dictionaries.
    config = {}
    for hostname in hosts:
        _, _, port, _ = read_openssh_config(hostname)
        config[hostname] = {"port": port}

    client = ParallelSSHClient(hosts, host_config=config, pkey=pkey)
    output = client.run_command("./spout")
    print("Finished initialization.")

    funnel, _ = mp.Pipe()
    p = mp.Process(target=listener, args=(funnel,))

    return output


# Pickle a sample function.
def useless():
    """ Function to be pickled. """
    print("Hello there!")


def test_init():
    """ Test speed of SSH client stdin against a benchmark. """
    # Define private key path and hostnames.
    pkey = ".ssh/id_rsa"
    hosts = ["cc-16", "cc-17", "cc-18", "cc-19", "cc-20"]

    # Per-host config dictionaries.
    config = {}
    for hostname in hosts:
        _, _, port, _ = read_openssh_config(hostname)
        config[hostname] = {"port": port}

    # Instantiate parallel SSH connections.
    client = ParallelSSHClient(hosts, host_config=config, pkey=pkey)
    # message = pickle.dumps(useless)

    # Run ``benchmark.c``, which reads continuously from stdin, and measures the
    # time between writes delimited by newlines.
    output = client.run_command("./a.out")

    # Grab references to stdin streams.
    stdins = [out.stdin for out in output.values()]

    # Write several strings to stdin.
    for i in range(10):
        print(i)
        for stdin in stdins:
            stdin.write("aaa-%d\n" % i)
        time.sleep(0.3)

    # Tell ``benchmark.c`` that we're done writing, so program exits.
    print("Sending quits.")
    for stdin in stdins:
        stdin.write("quit\n")

    # Display the output.
    for host, out in output.items():
        for line in out.stdout:
            if line.strip():
                print("Host %s: %s" % (host, line))

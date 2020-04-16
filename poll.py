import time
import pickle
from pssh.clients import ParallelSSHClient
from pssh.utils import read_openssh_config


def init():
    # Define private key path and hostnames.
    # TODO: Read config.
    pkey = ".ssh/id_rsa"
    hosts = ["cc-16", "cc-17", "cc-18", "cc-19", "cc-20"]

    # Per-host config dictionaries.
    config = {}
    for hostname in hosts:
        _, _, port, _ = read_openssh_config(hostname)
        config[hostname] = {"port": port}

    # Instantiate parallel SSH connections.
    client = ParallelSSHClient(hosts, host_config=config, pkey=pkey)
    output = client.run_command("./spout")

    return output


# Pickle a sample function.
def useless():
    print("Hello there!")


def test_init():
    """ Test speed of SSH client stdin against a benchmark. """
    # Define private key path and hostnames.
    # TODO: Read config.
    pkey = ".ssh/id_rsa"
    hosts = ["cc-16", "cc-17", "cc-18", "cc-19", "cc-20"]

    # Per-host config dictionaries.
    config = {}
    for hostname in hosts:
        _, _, port, _ = read_openssh_config(hostname)
        config[hostname] = {"port": port}

    # Instantiate parallel SSH connections.
    client = ParallelSSHClient(hosts, host_config=config, pkey=pkey)
    message = pickle.dumps(useless)

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

""" Function to parse hostnames from OpenSSH config file. """
import os
import socket
from typing import List
from paramiko import SSHConfig

# pylint: disable=too-few-public-methods


def get_available_hostnames_from_sshconfig(config_file: str = "") -> List[str]:
    """
    Parses user's OpenSSH config for per hostname configuration for
    hostname, user, port and private key values

    Parameters
    ----------
    config_file : ``str``.
        Path to config file.

    Returns
    -------
    hostnames : ``List[str]``.
        Found hostnames.
    """
    # Find config file.
    _ssh_config_file = (
        config_file
        if config_file
        else os.path.sep.join([os.path.expanduser("~"), ".ssh", "config"])
    )

    # Make sure config file exists.
    if not os.path.isfile(_ssh_config_file):
        return []

    # Read hostnames from paramiko config object.
    ssh_config = SSHConfig()
    ssh_config.parse(open(_ssh_config_file))
    raw_hostnames = ssh_config.get_hostnames()

    # Remove wildcards.
    hostnames = [name for name in raw_hostnames if "*" not in name]

    # Remove localhost.
    local = socket.gethostname()
    if local in hostnames:
        hostnames.remove(local)
    hostnames = sorted(hostnames)

    return hostnames

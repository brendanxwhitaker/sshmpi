""" SSHMPI utilities. """
import os
import socket
import functools
from typing import List
from paramiko import SSHConfig


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
    _ssh_config_file = (
        config_file
        if config_file
        else os.path.sep.join([os.path.expanduser("~"), ".ssh", "config"])
    )
    # Load ~/.ssh/config if it exists to pick up username
    # and host address if set
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
    hostnames.remove(local)
    hostnames = sorted(hostnames)

    return hostnames


def partialclass(cls, *args, **kwargs):
    """ Like ``functools.partial``, but for a class instantiator. """

    class Cls(cls):
        __init__ = functools.partialmethod(cls.__init__, *args, **kwargs)

    return Cls

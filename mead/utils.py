""" Function to parse hostnames from OpenSSH config file. """
import os
import socket
import struct
from typing import List, Tuple

import dill
from paramiko import SSHConfig

# pylint: disable=too-few-public-methods


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


def get_length_message_pair(obj: object) -> bytes:
    """ Pickles an object and returns bytes of a length+message pair. """
    message: bytes = dill.dumps(obj)

    # Get representation of then length of ``message`` in bytes.
    length = str(len(message)).encode("ascii")
    assert len(length) <= 16

    # Compute the pad so that prefix is a 16-byte sequence.
    padsize = 16 - len(length)
    pad = ("0" * padsize).encode("ascii")

    # Concatenate prefix and message.
    parcel = pad + length + message

    return parcel

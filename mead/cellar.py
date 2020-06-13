""" Storage for ``mead``. """
import multiprocessing as mp
from typing import Set, Dict, List
from multiprocessing.connection import Connection

from pssh.clients import ParallelSSHClient

# TODO: Consider overriding getattr on ``cellar`` to tell the user they
# need to run ``mead.init()`` first if they try to start a
# ``mead.Process``.

PIPE_COUNTER = 0
HOSTNAMES: List[str] = []
SSHCLIENT: ParallelSSHClient
USED_PIPE_IDS: Set[str] = set()
HEAD_QUEUES: Dict[str, mp.Queue] = {}
HEAD_SPOUTS: Dict[str, Connection] = {}
HEAD_PROCESSES: Dict[str, mp.Process] = {}
INTERNAL_FUNNELS: Dict[str, Connection] = {}
INTERNAL_SPOUTS: Dict[str, Connection] = {}

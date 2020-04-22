""" Storage for ``mead``. """
from typing import Set, Dict, List
import multiprocessing as mp
from multiprocessing.connection import Connection

PIPE_COUNTER = 0
HOSTNAMES: List[str] = []
USED_PIPE_IDS: Set[str] = set()
HEAD_QUEUES: Dict[str, mp.Queue] = {}
HEAD_SPOUTS: Dict[str, Connection] = {}
INTERNAL_FUNNELS: Dict[str, Connection] = {}
INTERNAL_SPOUTS: Dict[str, Connection] = {}

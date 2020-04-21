""" Storage for ``mead``. """
from typing import Set, Dict, List
from multiprocessing.connection import Connection

PIPE_COUNTER = 0
HOSTNAMES: List[str] = []
USED_PIPE_IDS: Set[str] = set()
HEAD_FUNNELS: Dict[str, Connection] = {}
HEAD_SPOUTS: Dict[str, Connection] = {}
INTERNAL_FUNNELS: Dict[str, Connection] = {}
INTERNAL_SPOUTS: Dict[str, Connection] = {}

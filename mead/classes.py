""" Classes for node-to-node communication over UDP. """
import random
import logging
from typing import Tuple, Dict, Optional, Any, Callable

import multiprocessing as mp
from multiprocessing.connection import Connection

from mead import cellar

# pylint: disable=too-few-public-methods


class Process:
    """ An analogue of ``mp.Process`` for mead serialization. """

    def __init__(
        self,
        target: Callable[..., Any],
        hostname: str = "",
        args: Optional[Tuple[Any, ...]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.hostname: str = hostname
        self.target: Callable[..., Any] = target
        self.args: Tuple[Any, ...]
        self.kwargs: Dict[str, Any]
        if self.hostname == "":
            self.hostname = cellar.HOSTNAMES[-1]
        if args:
            self.args = args
        else:
            self.args = ()
        if kwargs:
            self.kwargs = kwargs
        else:
            self.kwargs = {}

    # TODO: Add functionality for killing a ``mead.Process``.

    def start(self) -> None:
        """ Runs client on head node. Called by ``mp.Process``. """
        hostname = self.hostname

        # Send an instruction to start ``self: mead.Process`` on remote.
        cellar.HEAD_QUEUES[hostname].put(self)
        cellar.HEAD_QUEUES[hostname].put(self.target)

        # Aggregate the pipes from ``cellar`` which were passed to ``mead.Process``.
        injection_funnels: Dict[str, Connection] = {}
        extraction_spouts: Dict[str, Connection] = {}

        for arg in self.args:
            if isinstance(arg, Funnel):
                _spout = cellar.INTERNAL_SPOUTS[arg.pipe_id]
                extraction_spouts[arg.pipe_id] = _spout
            elif isinstance(arg, Spout):
                _funnel = cellar.INTERNAL_FUNNELS[arg.pipe_id]
                injection_funnels[arg.pipe_id] = _funnel

        for _name, arg in self.kwargs:
            if isinstance(arg, Funnel):
                _spout = cellar.INTERNAL_SPOUTS[arg.pipe_id]
                extraction_spouts[arg.pipe_id] = _spout
            elif isinstance(arg, Spout):
                _funnel = cellar.INTERNAL_FUNNELS[arg.pipe_id]
                injection_funnels[arg.pipe_id] = _funnel

        # Create and start the injection process.
        inject_args = (cellar.HEAD_SPOUTS[hostname], injection_funnels)
        p_inject = mp.Process(target=inject, args=inject_args)
        p_inject.start()

        # Create and start the extraction processes.
        extraction_processes: Dict[str, mp.Process] = {}
        for pipe_id, extraction_spout in extraction_spouts.items():
            extract_args = (pipe_id, cellar.HEAD_QUEUES[hostname], extraction_spout)
            p_extract = mp.Process(target=extract, args=extract_args)
            p_extract.start()
            extraction_processes[pipe_id] = p_extract


def inject(in_spout: Connection, injection_funnels: Dict[str, Connection]) -> None:
    """ Receives data from the client and forwards it to a local process. """
    while 1:
        logging.info("INJECTION: waiting.")
        parcel = in_spout.recv()
        logging.info("INJECTION: parcel: %s", str(parcel))
        if not isinstance(parcel, Parcel):
            logging.info("INJECTION: Error: obj not a Parcel: %s", str(parcel))

        assert isinstance(parcel, Parcel)
        assert not isinstance(parcel.obj, Parcel)
        injection_funnels[parcel.pipe_id].send(parcel.obj)


def extract(pipe_id: str, out_queue: mp.Queue, extraction_spout: Connection) -> None:
    """ Receives data from a local process and forwards it to the client. """
    while 1:
        obj = extraction_spout.recv()
        logging.info("EXTRACTION: obj: %s", str(obj))
        assert not isinstance(obj, Parcel)
        parcel = Parcel(pipe_id, obj)
        out_queue.put(parcel)


class Parcel:
    """ An object to carry an arbitrary python object with an identifier. """

    def __init__(self, pipe_id: str, obj: Any):
        self.pipe_id = pipe_id
        self.obj = obj


class Funnel:
    """ TODO. """

    def __init__(self, pipe_id: str, _funnel: Connection):
        self.pipe_id = pipe_id
        self._funnel = _funnel

    def send(self, data: Any) -> None:
        """ Send data (presumably to a remote node). """
        assert not isinstance(data, Parcel)
        logging.info("FUNNEL: data: %s", str(data))
        self._funnel.send(data)


class Spout:
    """ TODO. """

    def __init__(self, pipe_id: str, _spout: Connection):
        self.pipe_id = pipe_id
        self._spout = _spout

    def recv(self) -> Any:
        """ Receive data (presumably from a remote node). """
        data = self._spout.recv()
        assert not isinstance(data, Parcel)
        return data


# pylint: disable=invalid-name
def Pipe() -> Tuple[Funnel, Spout]:
    """ Creates a ``mead.Pipe`` pair. """

    # Get a unique pipe id.
    pipe_id = str(cellar.PIPE_COUNTER)
    cellar.USED_PIPE_IDS.add(pipe_id)
    cellar.PIPE_COUNTER += 1

    # Create internal multiprocessing pipe.
    _funnel, _spout = mp.Pipe()
    cellar.INTERNAL_FUNNELS[pipe_id] = _funnel
    cellar.INTERNAL_SPOUTS[pipe_id] = _spout

    # Create mead funnel and spout.
    funnel = Funnel(pipe_id, _funnel)
    spout = Spout(pipe_id, _spout)

    return funnel, spout

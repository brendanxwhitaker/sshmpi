""" Classes for node-to-node communication over UDP. """
import sys
import signal
import logging
from typing import Tuple, Dict, Optional, Any, Callable, List, Union

import multiprocessing as mp
from multiprocessing.connection import Connection

import dill
from mead import cellar

# pylint: disable=too-few-public-methods


class _Spout:
    def __init__(self, pipe_id: str):
        self.pipe_id = pipe_id


class _Funnel:
    def __init__(self, pipe_id: str):
        self.pipe_id = pipe_id


class _Process:
    def __init__(
        self,
        target: Callable[..., Any],
        hostname: str,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ):
        self.hostname: str = hostname
        self.target: Callable[..., Any] = target
        self.args: Tuple[Any, ...] = args
        self.kwargs: Dict[str, Any] = kwargs


class _Join:
    def __init__(self, hostname: str):
        self.hostname = hostname


class _Terminate:
    def __init__(self, hostname: str):
        self.hostname = hostname


class _Kill:
    def __init__(self, hostname: str):
        self.hostname = hostname


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
            # TODO: Handle IndexError when HOSTNAMES is empty.
            self.hostname = cellar.HOSTNAMES[-1]
        if args:
            self.args = args
        else:
            self.args = ()
        if kwargs:
            self.kwargs = kwargs
        else:
            self.kwargs = {}

        self.aux_spout: Connection
        self.p_inject: mp.Process
        self.extraction_processes: Dict[str, mp.Process]

    def join(self, timeout: Optional[Union[float, int]] = None) -> None:
        """ Blocks until the process terminates. """
        join = _Join(self.hostname)
        cellar.HEAD_QUEUES[self.hostname].put(join)
        reply = self.aux_spout.recv()
        if isinstance(reply, _Join):
            logging.info("Remote process joined.")
            self.p_inject.terminate()
            self.p_inject.join()
            for _, p in self.extraction_processes.items():
                p.terminate()
                p.join()

    def terminate(self) -> None:
        """ Terminates the process with SIGTERM. """
        raise NotImplementedError

    def kill(self) -> None:
        """ Terminates the process with SIGKILL. """
        raise NotImplementedError

    def start(self) -> None:
        """ Runs client on head node. Called by ``mp.Process``. """
        hostname = self.hostname

        # Iterate over the arguments, replacing mead pipes with mp pipes.
        mp_args: List[Any] = []
        for arg in self.args:
            if isinstance(arg, Funnel):
                funnel = _Funnel(arg.pipe_id)
                mp_args.append(funnel)
            elif isinstance(arg, Spout):
                spout = _Spout(arg.pipe_id)
                mp_args.append(spout)
            else:
                mp_args.append(arg)

        # Iterate over the keyword arguments, replacing mead pipes with mp pipes.
        mp_kwargs: Dict[str, Any] = {}
        for name, arg in self.kwargs.items():
            if isinstance(arg, Funnel):
                funnel = _Funnel(arg.pipe_id)
                mp_kwargs[name] = funnel
            elif isinstance(arg, Spout):
                spout = _Spout(arg.pipe_id)
                mp_kwargs[name] = spout
            else:
                mp_kwargs[name] = arg

        # Creata a placeholder process object to hold target and arguments.
        _process = _Process(self.target, self.hostname, tuple(mp_args), mp_kwargs)

        # Send an instruction to start ``self: mead.Process`` on remote.
        cellar.HEAD_QUEUES[hostname].put(_process)

        # Aggregate the pipes from ``cellar`` which were passed to ``mead.Process``.
        injection_funnels: Dict[str, Connection] = {}
        extraction_spouts: Dict[str, Connection] = {}

        for arg in self.args:
            if isinstance(arg, Funnel):
                _funnel = cellar.INTERNAL_FUNNELS[arg.pipe_id]
                injection_funnels[arg.pipe_id] = _funnel
            elif isinstance(arg, Spout):
                _spout = cellar.INTERNAL_SPOUTS[arg.pipe_id]
                extraction_spouts[arg.pipe_id] = _spout

        for _name, arg in self.kwargs:
            if isinstance(arg, Funnel):
                _funnel = cellar.INTERNAL_FUNNELS[arg.pipe_id]
                injection_funnels[arg.pipe_id] = _funnel
            elif isinstance(arg, Spout):
                _spout = cellar.INTERNAL_SPOUTS[arg.pipe_id]
                extraction_spouts[arg.pipe_id] = _spout

        aux_funnel, aux_spout = mp.Pipe()
        self.aux_spout = aux_spout

        # Create and start the injection process.
        inject_args = (cellar.HEAD_SPOUTS[hostname], injection_funnels, aux_funnel)
        p_inject = mp.Process(target=inject, args=inject_args)
        p_inject.start()
        self.p_inject = p_inject

        # Create and start the extraction processes.
        extraction_processes: Dict[str, mp.Process] = {}
        for pipe_id, extraction_spout in extraction_spouts.items():

            logging.info("START: extracting from pipe: %s", pipe_id)
            extract_args = (pipe_id, cellar.HEAD_QUEUES[hostname], extraction_spout)
            p_extract = mp.Process(target=extract, args=extract_args)
            p_extract.start()
            extraction_processes[pipe_id] = p_extract
        self.extraction_processes = extraction_processes


def inject(
    in_spout: Connection,
    injection_funnels: Dict[str, Connection],
    aux_funnel: Optional[Connection] = None,
) -> None:
    """ Receives data from the client and forwards it to a local process. """

    # Exit when SIGTERM is sent, i.e. when we call .terminate().
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit())

    while 1:
        logging.info("INJECTION: waiting.")
        bparcel = in_spout.recv()
        parcel = dill.loads(bparcel)

        # Handle process signals.
        if aux_funnel and isinstance(parcel, (_Join, _Terminate, _Kill)):
            logging.info("INJECTION: got signal.")
            aux_funnel.send(parcel)
            continue

        # If the received object is not a signal, it ought to be a parcel.
        if not isinstance(parcel, Parcel):
            logging.info("INJECTION: Error: obj not a Parcel: %s", str(parcel))

        assert isinstance(parcel, Parcel)
        assert not isinstance(parcel.obj, Parcel)
        logging.info("INJECTION: parcel: %s for pipe: %s", str(parcel), parcel.pipe_id)
        injection_funnels[parcel.pipe_id].send(parcel.obj)


def extract(pipe_id: str, out_queue: mp.Queue, extraction_spout: Connection) -> None:
    """ Receives data from a local process and forwards it to the client. """

    # Exit when SIGTERM is sent, i.e. when we call .terminate().
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit())

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
        logging.info("FUNNEL: pipe id: %s", self.pipe_id)
        self._funnel.send(data)


class Spout:
    """ TODO. """

    def __init__(self, pipe_id: str, _spout: Connection):
        self.pipe_id = pipe_id
        self._spout = _spout

    def recv(self) -> Any:
        """ Receive data (presumably from a remote node). """
        logging.info("SPOUT: waiting.")
        data = self._spout.recv()
        logging.info("SPOUT: data: %s", str(data))
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

""" Classes for node-to-node communication over UDP. """
import logging
import multiprocessing as mp
from typing import Any, Dict, Tuple, Union, Callable, Optional
from multiprocessing.connection import Connection

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
    def __init__(self, hostname: str, timeout: Optional[Union[float, int]]):
        self.hostname = hostname
        self.timeout = timeout


class _Terminate:
    def __init__(self, hostname: str):
        self.hostname = hostname


class _Kill:
    def __init__(self, hostname: str):
        self.hostname = hostname


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

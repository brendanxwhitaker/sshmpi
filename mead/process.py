""" The ``mead.Process`` class, analogous to ``mp.Process``. """
import logging
import multiprocessing as mp
from typing import Any, Dict, Tuple, Union, Callable, Optional
from multiprocessing.connection import Connection

from mead import cellar
from mead.classes import _Join, _Process
from mead.transport import inject, extract
from mead.connections import get_head_connections


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
        self.p_in: mp.Process
        self.p_outs: Dict[str, mp.Process]

    def join(self, timeout: Optional[Union[float, int]] = None) -> None:
        """ Blocks until the process terminates. """
        join = _Join(self.hostname, timeout)
        cellar.HEAD_QUEUES[self.hostname].put(join)
        reply = self.aux_spout.recv()
        if isinstance(reply, _Join):
            logging.info("Remote process joined.")
            self.p_in.terminate()
            self.p_in.join()
            for _, p in self.p_outs.items():
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

        # Replace e.g. ``mead.Funnel`` with ``mead._Funnel``.
        # Retrieve refs to internal funnels and spouts leading to head process pipes.
        in_funnels, out_spouts, mp_args, mp_kwargs = get_head_connections(
            self.args, self.kwargs
        )

        # Creata a placeholder process object to hold target and arguments.
        _process = _Process(self.target, self.hostname, mp_args, mp_kwargs)

        # Send an instruction to start ``self: mead.Process`` on remote.
        cellar.HEAD_QUEUES[self.hostname].put(_process)
        cellar.HEAD_QUEUES[self.hostname].put(_process)
        cellar.HEAD_QUEUES[self.hostname].put(_process)

        aux_funnel, aux_spout = mp.Pipe()
        self.aux_spout = aux_spout

        # Create and start the in process.
        head_spout = cellar.HEAD_SPOUTS[self.hostname]
        self.p_in = mp.Process(target=inject, args=(head_spout, in_funnels, aux_funnel))
        self.p_in.start()

        # Create and start the out processes.
        self.p_outs = {}
        for pipe_id, out_spout in out_spouts.items():
            logging.info("START: extracting from pipe: %s", pipe_id)
            head_queue = cellar.HEAD_QUEUES[self.hostname]
            p_out = mp.Process(target=extract, args=(pipe_id, head_queue, out_spout))
            p_out.start()
            self.p_outs[pipe_id] = p_out

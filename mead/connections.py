""" Functions for construction connection maps between processes and clients. """
import multiprocessing as mp
from typing import Any, Dict, List, Tuple
from multiprocessing.connection import Connection

from mead import cellar
from mead.classes import Spout, Funnel, _Spout, _Funnel


def get_head_connections(
    args: Tuple[Any, ...], kwargs: Dict[str, Any]
) -> Tuple[
    Dict[str, Connection], Dict[str, Connection], Tuple[Any, ...], Dict[str, Any],
]:
    """ Replaces e.g. ``Funnel`` with ``_Funnel`` for serialization. """

    # Aggregate the pipes from ``cellar`` which were passed to ``mead.Process``.
    in_funnels: Dict[str, Connection] = {}
    out_spouts: Dict[str, Connection] = {}

    # Construct serializable argument lists with mead placeholders.
    mp_args: List[Any] = []
    mp_kwargs: Dict[str, Any] = {}

    for arg in args:
        if isinstance(arg, Funnel):
            funnel = cellar.INTERNAL_FUNNELS[arg.pipe_id]
            in_funnels[arg.pipe_id] = funnel
            _funnel = _Funnel(arg.pipe_id)
            mp_args.append(_funnel)
        elif isinstance(arg, Spout):
            spout = cellar.INTERNAL_SPOUTS[arg.pipe_id]
            out_spouts[arg.pipe_id] = spout
            _spout = _Spout(arg.pipe_id)
            mp_args.append(_spout)
        else:
            mp_args.append(arg)

    for name, arg in kwargs.items():
        if isinstance(arg, Funnel):
            funnel = cellar.INTERNAL_FUNNELS[arg.pipe_id]
            in_funnels[arg.pipe_id] = funnel
            _funnel = _Funnel(arg.pipe_id)
            mp_kwargs[name] = _funnel
        elif isinstance(arg, Spout):
            spout = cellar.INTERNAL_SPOUTS[arg.pipe_id]
            out_spouts[arg.pipe_id] = spout
            _spout = _Spout(arg.pipe_id)
            mp_kwargs[name] = _spout
        else:
            mp_kwargs[name] = arg

    return in_funnels, out_spouts, tuple(mp_args), mp_kwargs


def get_remote_connections(
    args: Tuple[Any, ...], kwargs: Dict[str, Any]
) -> Tuple[
    Dict[str, Connection], Dict[str, Connection], Tuple[Any, ...], Dict[str, Any]
]:
    """ Gets in funnels and out spouts for a remote process. """

    # Aggregate the pipes from ``cellar`` which were passed to ``mead.Process``.
    in_funnels: Dict[str, Connection] = {}
    out_spouts: Dict[str, Connection] = {}

    mp_args: List[Any] = []
    mp_kwargs: Dict[str, Any] = {}

    # Iterate over the arguments, replacing mead pipes with mp pipes.
    for arg in args:
        if isinstance(arg, _Funnel):
            funnel, spout = mp.Pipe()
            out_spouts[arg.pipe_id] = spout
            mp_args.append(funnel)
        elif isinstance(arg, _Spout):
            funnel, spout = mp.Pipe()
            in_funnels[arg.pipe_id] = funnel
            mp_args.append(spout)
        else:
            mp_args.append(arg)

    # Iterate over the keyword arguments, replacing mead pipes with mp pipes.
    for name, arg in kwargs.items():
        if isinstance(arg, _Funnel):
            funnel, spout = mp.Pipe()
            out_spouts[arg.pipe_id] = spout
            mp_kwargs[name] = funnel
        elif isinstance(arg, _Spout):
            funnel, spout = mp.Pipe()
            in_funnels[arg.pipe_id] = funnel
            mp_kwargs[name] = spout
        else:
            mp_kwargs[name] = arg

    return in_funnels, out_spouts, tuple(mp_args), mp_kwargs

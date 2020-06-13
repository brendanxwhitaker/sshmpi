""" Functions for forwarding data between processes and clients. """
import sys
import signal
import logging
import multiprocessing as mp
from typing import Dict, Optional
from multiprocessing.connection import Connection

import dill

from mead.classes import Parcel, _Join, _Kill, _Terminate


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
            continue

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

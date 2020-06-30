""" Starts processes for a remote client. Called by ``meadclient``. """
import os
import sys
import logging
import multiprocessing as mp
from typing import Dict
from multiprocessing.connection import Connection

import stun
import dill

from mead.client import Client
from mead.classes import _Join, _Process
from mead.transport import inject, extract
from mead.connections import get_remote_connections


def remote(head_ip: str, port: int, channel: str) -> None:
    """ Runs the client for a remote worker. """
    logging.basicConfig(filename="remote.log", level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # Get external IP and port from STUN server.
    _, external_ip, external_port = stun.get_ip_info(source_port=50000)

    # Write sockaddr to file.
    sockpath = os.path.abspath(os.path.expanduser("~/.sockaddr.mead"))
    with open(sockpath, "w") as sockfile:
        sockfile.write(external_ip + "\n")
        sockfile.write(str(external_port) + "\n")

    # Transport in and out of the head node.
    in_funnel, in_spout = mp.Pipe()
    out_queue: mp.Queue = mp.Queue()
    aux_funnel, aux_spout = mp.Pipe()

    # Create and start the client.
    client = Client(head_ip, port, channel, in_funnel, out_queue)
    p_client = mp.Process(target=client.main)
    p_client.start()

    while 1:
        logging.info("REMOTE: waiting for a ``_Process``.")
        bprocess = in_spout.recv()
        p = dill.loads(bprocess)

        if isinstance(p, _Process):
            logging.info("REMOTE: starting user process.")

            # Start the process.
            p_remote = start(p, in_spout, out_queue, aux_funnel)

            logging.info("REMOTE: break.")
            break

        logging.info("ERR: p not _Process: %s", p)

    while 1:
        sig = aux_spout.recv()
        if isinstance(sig, _Join):
            logging.info("REMOTE: Joining.")
            out_queue.put(sig)
            p_remote.join(timeout=sig.timeout)


def start(
    p: _Process, in_spout: Connection, out_queue: mp.Queue, aux_funnel: Connection
) -> mp.Process:
    """ Starts a deserialized remote process. """
    # Connects pipes in transport processes to pipes in ``p_remote``.
    in_funnels, out_spouts, mp_args, mp_kwargs = get_remote_connections(
        p.args, p.kwargs
    )

    logging.info("REMOTE: in funnels: %s:", str(in_funnels))
    logging.info("REMOTE: mpargs: %s:", str(mp_args))

    # Start the deserialized process.
    p_remote = mp.Process(target=p.target, args=mp_args, kwargs=mp_kwargs)
    p_remote.start()

    # Transport process to read from the client and write to ``p_remote``.
    p_in = mp.Process(target=inject, args=(in_spout, in_funnels, aux_funnel))
    p_in.start()

    # Transport processes to read from ``p_remote`` and write to the client.
    p_outs: Dict[str, mp.Process] = {}
    for pipe_id, out_spout in out_spouts.items():
        p_out = mp.Process(target=extract, args=(pipe_id, out_queue, out_spout))
        p_out.start()
        p_outs[pipe_id] = p_out

    return p_remote

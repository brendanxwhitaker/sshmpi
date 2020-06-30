""" An example of how to pass messages between nodes with ``mead``. """
import sys
import time
import logging

import mead
from mead.utils import get_available_hostnames_from_sshconfig

logging.basicConfig(filename="mead.log", level=logging.DEBUG)
# logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def augment(funnel: mead.Funnel, spout: mead.Spout, n: int) -> None:
    """ Augments an integer. """
    # TODO: Dill the whole interpreter session during ``init()`` call so that
    # imports are all defined properly.
    while 1:
        liquid = spout.recv()
        liquid += 1
        funnel.send(liquid)
        if liquid == n:
            break


def main() -> None:
    """ Runs a simple example of ``mead`` usage. """

    # When you instantiate a mead pipe, it instantiates a multiprocessing pipe
    # in its ``__init__`` function. It stores both ends of this internal pipe
    # inside a global storage module in mead. When you instantiate a
    # ``mead.Process`` and pass either the ``mead.Funnel`` or the
    # ``mead.Spout`` as an argument, the corresponding end of the internal pipe
    # is retrieved from the storage module, and passed in a dictionary to the
    # ``head`` client function, which runs a ``mead.Client`` to pass data to
    # and from a remote node. If you use the ``mead.Pipe`` locally, it will
    # work just like its multiprocessing counterpart. If you try to pass both
    # ends of the pipe to a ``mead.Process``, it will raise an error.

    # A ``mead.Process`` runs on exactly one (remote) node.
    mead.init("local.json")
    in_funnel, in_spout = mead.Pipe()
    out_funnel, out_spout = mead.Pipe()
    hosts = get_available_hostnames_from_sshconfig()
    hosts = ["localhost"]
    print("Hosts:", hosts)

    n = 1000
    for hostname in hosts:
        p = mead.Process(
            target=augment, hostname=hostname, args=(out_funnel, in_spout, n)
        )
        p.start()

        i = 0
        times = []
        t = time.time()
        while i < n:
            times.append(time.time() - t)
            t = time.time()
            in_funnel.send(i)
            i = out_spout.recv()
        times = times[2:]
        mean = sum(times) / max(1, len(times))
        print("Mean latency: %s: %fs" % (hostname, mean))
        p.join()
    mead.kill()


if __name__ == "__main__":
    main()

""" An example of how to pass messages between nodes with ``mead``. """
import mead


def augment(funnel: mead.Funnel, spout: mead.Spout) -> None:
    """ Augments an integer. """
    while 1:
        liquid = spout.recv()
        liquid += 1
        funnel.send(liquid)


def main() -> None:
    """ Runs a simple example of ``mead`` usage. """
    mead.init()
    in_funnel, in_spout = mead.Pipe()
    out_funnel, out_spout = mead.Pipe()

    # TODO: Change over to queue for anything where we have multiple producers
    # or consumers.

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

    p = mead.Process(target=augment, args=(in_spout, out_funnel))
    p.start()

    i = 0
    while i < 1000:
        in_funnel.send(i)
        i = out_spout.recv()

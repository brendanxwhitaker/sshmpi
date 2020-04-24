""" An example of how to pass messages between nodes with ``mead``. """
import mead


def augment(funnel: mead.Funnel, spout: mead.Spout) -> None:
    """ Augments an integer. """
    # TODO: Dill the whole interpreter session during ``init()`` call so that
    # imports are all defined properly.
    import time

    times = []
    t = time.time()
    while 1:
        print("Loop: %f" % (time.time() - t))
        times.append(time.time() - t)
        t = time.time()
        liquid = spout.recv()
        liquid += 1
        funnel.send(liquid)
        if liquid == 100:
            break
    mean = sum(times) / len(times)
    funnel.send(mean)


def main() -> None:
    """ Runs a simple example of ``mead`` usage. """
    mead.init("local.json")
    in_funnel, in_spout = mead.Pipe()
    out_funnel, out_spout = mead.Pipe()

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

    p = mead.Process(target=augment, hostname="cc-2", args=(out_funnel, in_spout))
    p.start()

    i = 0
    while i < 100:
        in_funnel.send(i)
        i = out_spout.recv()
    mean = out_spout.recv()
    print("Mean: %fs" % mean)
    p.join()
    mead.kill()


if __name__ == "__main__":
    main()

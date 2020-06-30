import multiprocessing as mp
from mead.pysrt import (
    mead_startup,
    mead_rendezvous,
    mead_rendezvous_test,
    mead_sendmsg2,
    mead_recvmsg2,
    mead_close,
    mead_cleanup,
)


def peer():
    print("peer started.")
    mead_startup()
    socket = mead_rendezvous_test("76.16.39.133", 50000, 50001)
    print("socket:", socket)
    mead_sendmsg2(socket, "hi.")
    msg = mead_recvmsg2(socket, 4096)
    mead_close(socket)
    mead_cleanup()
    print("msg:", msg)


def main():
    """
    q = mp.Process(target=peer, args=())
    q.start()
    """
    p = mp.Process(target=peer, args=())
    p.start()

    print("peer started.")
    input()
    mead_startup()
    socket = mead_rendezvous_test("76.16.39.133", 50002, 50003)
    print("socket:", socket)
    mead_sendmsg2(socket, "hi.")
    msg = mead_recvmsg2(socket, 4096)
    mead_close(socket)
    mead_cleanup()
    print("msg:", msg)

    p.join()
    # q.join()


if __name__ == "__main__":
    main()

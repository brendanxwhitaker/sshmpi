import sys
import multiprocessing as mp
from mead.pysrt import (
    mead_startup,
    mead_rendezvous,
    mead_sendmsg2,
    mead_recvmsg2,
    mead_close,
    mead_cleanup,
)

def main():
    print("peer started.")
    input()
    mead_startup()
    socket = mead_rendezvous(sys.argv[1], 54320, sys.argv[2], 54320)
    print("socket:", socket)
    mead_sendmsg2(socket, "hi.")
    msg = mead_recvmsg2(socket, 4096)
    mead_close(socket)
    mead_cleanup()
    print("msg:", msg)


if __name__ == "__main__":
    main()

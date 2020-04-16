import os
import sys
import pickle

k = 0
nl = "\n".encode("ascii")
try:
    buf = b""
    while 1:
        # Read the length of the message given in 16 bytes.
        buf += sys.stdin.buffer.read(16)
        blength = buf
        length = int(blength.decode("ascii"))
        print("Decoded length:", length)

        # Read the message proper.
        buf = sys.stdin.buffer.read(length + 1)
        arr = pickle.loads(buf)
        print(arr)
        sys.stdout.write("Hello!!\n")
        sys.stdout.flush()
        buf = b""

except KeyboardInterrupt:
    sys.stdout.flush()
print(k)

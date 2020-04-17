import sys
import socket
from sshmpi.utils import get_available_hostnames_from_sshconfig


def main():
    hosts = get_available_hostnames_from_sshconfig()
    ip = socket.gethostbyname("0.tcp.ngrok.io")
    hostline = " ".join(hosts)
    line = "%s\t" % ip + " ".join(hosts)
    with open("/etc/hosts", "r") as hosts_file:
        lines = hosts_file.read().split("\n")
        if hostline in lines:
            sys.exit()
    with open("/etc/hosts", "a") as hosts_file:
        hosts_file.write(line + "\n")


if __name__ == "__main__":
    main()

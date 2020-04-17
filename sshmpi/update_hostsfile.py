import socket
from sshmpi.utils import get_available_hostnames_from_sshconfig


def main():
    hosts = get_available_hostnames_from_sshconfig()
    ip = socket.gethostbyname("0.tcp.ngrok.io")
    line = "%s\t" % ip + " ".join(hosts) + "\n"
    print(line)
    with open("/etc/hosts", "a") as hosts_file:
        hosts_file.write(line)


if __name__ == "__main__":
    main()

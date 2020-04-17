import subprocess
from sshmpi.utils import get_available_hostnames_from_sshconfig


def main():
    hosts = get_available_hostnames_from_sshconfig()
    p = subprocess.Popen(["ping", "0.tcp.ngrok.io"], stdout=subprocess.PIPE)
    print(p.stdout)

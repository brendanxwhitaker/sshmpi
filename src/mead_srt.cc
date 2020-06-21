/*
 * SRT - Secure, Reliable, Transport
 * Copyright (c) 2017 Haivision Systems Inc.
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 * 
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 * 
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; If not, see <http://www.gnu.org/licenses/>
 */


#include <stdio.h>
#include <stdlib.h>
#ifdef _WIN32
#define usleep(x) Sleep(x / 1000)
#else
#include <unistd.h>
#endif

#include <srt/srt.h>
#include <pybind11/pybind11.h>

namespace py = pybind11;

int mead_startup()
{
    printf("srt startup\n");
    srt_startup();
    return 0;
}


int mead_rendezvous(const char* remote_addr, int port)
{
    // These are the socket objects/identifiers, which are just integers.
    int socket, status;

    // Will contain address and port.
    struct sockaddr_in remote_sockaddr;
    struct sockaddr_in local_sockaddr;

    printf("srt socket\n");
    socket = srt_create_socket();
    if (socket == SRT_ERROR)
    {
        fprintf(stderr, "srt_socket: %s\n", srt_getlasterror_str());
        return 1;
    }

    // ==========================================================
    // ================ INITIALIZE SOCKADDRESS ==================
    printf("srt remote address\n");
    remote_sockaddr.sin_family = AF_INET;

    // Set the remote port.
    remote_sockaddr.sin_port = htons(port);

    // Load the remote IP address into the ``sockaddr_in`` object.
    if (inet_pton(AF_INET, remote_addr, &remote_sockaddr.sin_addr) != 1)
    {
        return 1;
    }
    // ================ INITIALIZE SOCKADDRESS ==================
    // ==========================================================

    // ==========================================================
    // ================ INITIALIZE SOCKADDRESS ==================
    printf("srt local address\n");
    local_sockaddr.sin_family = AF_INET;

    // Set the local port.
    local_sockaddr.sin_port = htons(port);

    // Load the local IP address into the ``sockaddr_in`` object.
    if (inet_pton(AF_INET, INADDR_ANY, &local_sockaddr.sin_addr) != 1)
    {
        return 1;
    }
    // ================ INITIALIZE SOCKADDRESS ==================
    // ==========================================================

    printf("srt rendezvous\n");
    status = srt_rendezvous(socket, (struct sockaddr*)&local_sockaddr, sizeof local_sockaddr, (struct sockaddr*)&remote_sockaddr, sizeof remote_sockaddr);
    if (status == SRT_ERROR)
    {
        fprintf(stderr, "srt_rendezvous: %s\n", srt_getlasterror_str());
        return 1;
    }

    return socket;
}

int mead_sendmsg2(int socket, const char* message)
{
    // These are the socket objects/identifiers, which are just integers.
    int status;

    printf("srt sendmsg2 >> %s\n",message);
    status = srt_sendmsg2(socket, message, sizeof message, NULL);
    if (status == SRT_ERROR)
    {
        fprintf(stderr, "srt_sendmsg: %s\n", srt_getlasterror_str());
        return 1;
    }
    return 0;
}

int mead_close(int socket)
{
    // These are the socket objects/identifiers, which are just integers.
    int status;

    printf("srt close\n");
    status = srt_close(socket);
    if (status == SRT_ERROR)
    {
        fprintf(stderr, "srt_close: %s\n", srt_getlasterror_str());
        return 1;
    }
    return 0;
}

int mead_cleanup()
{
    printf("srt cleanup\n");
    srt_cleanup();
    return 0;
}

PYBIND11_MODULE(mead_srt, m) {
    // optional module docstring
    m.doc() = "pybind11 srt plugin";

    // Define mead functions.
    m.def("mead_startup", &mead_startup, "");
    m.def("mead_rendezvous", &mead_rendezvous, "");
    m.def("mead_sendmsg2", &mead_sendmsg2, "");
    m.def("mead_cleanup", &mead_cleanup, "");

}

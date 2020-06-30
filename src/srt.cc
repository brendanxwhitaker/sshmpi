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

#include <srtcore/srt.h>
#include <pybind11/pybind11.h>

namespace py = pybind11;

int mead_startup()
{
    printf("srt startup\n");
    srt_startup();
    return 0;
}

int mead_sendmsg2(int socket, const char* message)
{
    // These are the socket objects/identifiers, which are just integers.
    int status;

    printf("srt sendmsg2 >> %s\n",message);
    status = srt_sendmsg2(socket, message, sizeof message, NULL);
    if (status == SRT_ERROR)
    {
        fprintf(stderr, "srt_sendmsg2: %s\n", srt_getlasterror_str());
        return 1;
    }
    return 0;
}

char* mead_recvmsg2(int socket, int buffer_size)
{
    // These are the socket objects/identifiers, which are just integers.
    int status;
    
    char *message = (char*)malloc(buffer_size + 1);
    strcpy(message, "SRT_ERROR");

    printf("srt recvmesg2 <<\n");
    status = srt_recvmsg2(socket, message, sizeof message - 1, NULL);
    if (status == SRT_ERROR)
    {
        fprintf(stderr, "srt_recvmsg2: %s\n", srt_getlasterror_str());
    }
    return message;
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

int mead_rendezvous(const char* remote_addr, int remote_port, int local_port)
{
    int ss, st;
    struct sockaddr_in lsa;
    struct sockaddr_in rsa;
    int yes = 1;
    struct sockaddr_storage their_addr;


    srt_setloglevel(LOG_DEBUG);

    printf("srt startup\n");
    srt_startup();

    printf("srt socket\n");
    ss = srt_create_socket();
    if (ss == SRT_ERROR)
    {
        fprintf(stderr, "srt_socket: %s\n", srt_getlasterror_str());
        return 1;
    }

    printf("srt bind address\n");
    lsa.sin_family = AF_INET;
    lsa.sin_port = htons(remote_port);
    if (inet_pton(AF_INET, "127.0.0.1", &lsa.sin_addr) != 1)
    {
        return 1;
    }

    printf("srt bind address\n");
    rsa.sin_family = AF_INET;
    rsa.sin_port = htons(remote_port);
    if (inet_pton(AF_INET, remote_addr, &rsa.sin_addr) != 1)
    {
        return 1;
    }

    printf("srt setsockflag\n");
    SRT_TRANSTYPE tt = SRTT_FILE;
    srt_setsockflag(ss, SRTO_RCVSYN, &yes, sizeof yes);
    srt_setsockflag(ss, SRTO_SENDER, &yes, sizeof yes);
    srt_setsockflag(ss, SRTO_TRANSTYPE, &tt, sizeof tt);
    srt_setsockflag(ss, SRTO_MESSAGEAPI, &yes, sizeof yes);
    srt_setsockopt(ss, 0, SRTO_RENDEZVOUS, &yes, sizeof yes);

    printf("srt bind\n");
    st = srt_bind(ss, (struct sockaddr*)&lsa, sizeof lsa);
    if (st == SRT_ERROR)
    {
        fprintf(stderr, "srt_bind: %s\n", srt_getlasterror_str());
        return 1;
    }

    printf("srt connect\n");
    st = srt_connect(ss, (struct sockaddr*)&rsa, sizeof rsa);
    if (st == SRT_ERROR)
    {
        fprintf(stderr, "srt_connect: %s\n", srt_getlasterror_str());
        return 1;
    }

    return ss;
}

PYBIND11_MODULE(pysrt, m) {
    // optional module docstring
    m.doc() = "pybind11 srt plugin";

    // Define mead functions.
    m.def("mead_startup", &mead_startup, "");
    m.def("mead_rendezvous", &mead_rendezvous, "");
    m.def("mead_sendmsg2", &mead_sendmsg2, "");
    m.def("mead_recvmsg2", &mead_recvmsg2, "");
    m.def("mead_close", &mead_close, "");
    m.def("mead_cleanup", &mead_cleanup, "");

}

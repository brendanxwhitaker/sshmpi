#include <time.h>
#include <stdio.h>
#include <string.h>

#define BUFFER_SIZE BUFSIZ

int main(int argc, const char **argv) {

    // Define buffer and make initial read.
    char i[BUFFER_SIZE];
    fgets(i, BUFSIZ, stdin);
    printf("Out: %s", i);

    struct timespec start, stop;

    // Continuously read from stdin.
    while (strcmp(i, "quit\n") != 0) {
        clock_gettime(CLOCK_REALTIME, &start); 
        fgets(i, BUFSIZ, stdin);
        clock_gettime(CLOCK_REALTIME, &stop); 
        double result = (stop.tv_sec - start.tv_sec) * 1e6 + (stop.tv_nsec - start.tv_nsec) / 1e3;
        printf("Elapsed microseconds: %f | Input: %s\n", result, i);
    }
    return 0;
}

#include "poly1305-donna.h"
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

uint8_t *msg, *key, *mac;
size_t msg_size;

#define KEY_SIZE 32
#define MAC_SIZE 16

int main(int argc, char **argv){

    srandom(clock());

    key = (uint8_t*)malloc(KEY_SIZE);
    mac = (uint8_t*)malloc(MAC_SIZE);

    for (int i = 0; i < KEY_SIZE; i++) key[i] = random() & 0x000000FF;

    msg_size = random() & 0x00000FFF;
    msg = (uint8_t*)malloc(msg_size);

    for (int i = 0; i < msg_size; i++) msg[i] = random() & 0x000000FF;

    poly1305_auth(mac, msg, msg_size, key);

    for (int i = 0; i < msg_size; i++)
        printf("%u%s", msg[i], (i == msg_size-1) ? "\n" : "," );
    for (int i = 0; i < KEY_SIZE; i++)
        printf("%u%s", key[i], (i == KEY_SIZE-1) ? "\n" : "," );
    for (int i = 0; i < MAC_SIZE; i++)
        printf("%u%s", mac[i], (i == MAC_SIZE-1) ? "\n" : "," );

    return 0;
}



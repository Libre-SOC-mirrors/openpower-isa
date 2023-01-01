/*************************************************************************
 * This is a simple program to calculate test vectors and compare them   *
 * to known good values for XChaCha20.
 *************************************************************************/
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "xchacha20.h"

/* implementation of memset to stop complaining */
void *memset(void *s, int c,  size_t len)
{
    unsigned char* p=s;
    while(len--)
    {
        *p++ = (unsigned char)c;
    }
    return s;
}

/** Compare our output to the output of a known good XChaCha20 library.
 * The test vectors used here are from examples given of the Crypto++
 * cryptographic library's XChaCha20 examples. These values can be
 * found here:
 * https://www.cryptopp.com/wiki/XChaCha20
 * @returns 0 on success, -1 on failure or error
 *
 */
int check_cpp(void){
	XChaCha_ctx ctx;
	uint8_t buffer[128];
	uint8_t counter[8] = {0x1};

	/* Test values from Crypto++ documentation */
	uint8_t key[] = {
			0x5E, 0xC5, 0x8B, 0x6D, 0x51, 0x4F, 0xE0, 0xA5,
			0x6F, 0x1E, 0x0D, 0xEA, 0x7B, 0xDC, 0x09, 0x5A,
			0x10, 0xF5, 0xB6, 0x18, 0xBD, 0xB6, 0xF2, 0x26,
			0x2F, 0xCC, 0x59, 0x7B, 0xB2, 0x30, 0xB3, 0xEF
	};

	uint8_t iv[] = {
			0xA3, 0x45, 0xF5, 0xCF, 0x80, 0x23, 0x51, 0x7C,
			0xC0, 0xFC, 0xF0, 0x75, 0x74, 0x8C, 0x86, 0x5F,
			0x7D, 0xE8, 0xCA, 0x0C, 0x72, 0x36, 0xAB, 0xDA
	};

	uint8_t correct_ciphertext[] = {
			0xEE, 0xA7, 0xC2, 0x71, 0x19, 0x10, 0x65, 0x69,
			0x92, 0xE1, 0xCE, 0xD8, 0x16, 0xE2, 0x0E, 0x62,
			0x1B, 0x25, 0x17, 0x82, 0x36, 0x71, 0x6A, 0xE4,
			0x99, 0xF2, 0x97, 0x37, 0xA7, 0x2A, 0xFC, 0xF8,
			0x6C, 0x72
	};

    // annoying: this is not word-aligned.
	uint8_t plaintext[] = "My Plaintext!! My Dear plaintext!!!";
	uint32_t msglen = strlen((char *)plaintext);

    /* knock one byte off the end */
    plaintext[msglen-1] = 0;
    msglen -= 1;

	xchacha_keysetup(&ctx, key, iv);

	/* Crypto++ initializes their counter to 1 instead of 0 */
	xchacha_set_counter(&ctx, counter);
	xchacha_encrypt_bytes(&ctx, plaintext, buffer, msglen);

	/* Compare our ciphertext to the correct ciphertext */
	if(memcmp(buffer, correct_ciphertext, msglen) != 0){
		return(-1);
	}

	return(0);
}

#define LOCATE_FUNC  __attribute__((__section__(".fixedaddr")))

int LOCATE_FUNC main(int argc, char **argv[]){
	return check_cpp();
}


#include <stdint.h>

typedef uint64_t bignum25519[5];

void curve25519_copy_svp64(bignum25519 out, const bignum25519 in);
void curve25519_copy_svp64_asm(bignum25519 out, const bignum25519 in);


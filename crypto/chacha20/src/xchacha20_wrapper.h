#include <stdint.h>

#include "xchacha20.h"

void xchacha_hchacha20_svp64_real(uint8_t *out, const uint8_t *in, const uint8_t *k);
void xchacha_hchacha20_svp64(uint8_t *out, const uint8_t *in, const uint8_t *k);

void xchacha_encrypt_bytes_svp64_real(XChaCha_ctx *ctx, const uint8_t *m, uint8_t *c, uint32_t bytes);
void xchacha_encrypt_bytes_svp64(XChaCha_ctx *ctx, const uint8_t *m, uint8_t *c, uint32_t bytes);

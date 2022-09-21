#include <stdint.h>

uint32_t vpx_get_mb_ss_svp64_real(const int16_t *src_ptr);

uint32_t vpx_get4x4sse_cs_svp64_real(const uint8_t *src_ptr, int src_stride,
                                     const uint8_t *ref_ptr, int ref_stride);


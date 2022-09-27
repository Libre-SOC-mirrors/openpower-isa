#include "vpx_integer.h"

#ifdef __cplusplus
extern "C" {
#endif

void vp8_short_fdct4x4_c(int16_t *input, int16_t *output, int32_t pitch);
void vp8_short_fdct4x4_svp64(int16_t *input, int16_t *output, int32_t pitch);

#ifdef __cplusplus
}  // extern "C"
#endif


/*
 *  Copyright (c) 2010 The WebM project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include <stdint.h>

#include "variance_svp64_wrappers.h"

#define DECLARE_ALIGNED(n, typ, val) typ val __attribute__((aligned(n)))

#define ROUND_POWER_OF_TWO(value, n) (((value) + (1 << ((n)-1))) >> (n))

#define FILTER_BITS 7

#define VAR(W, H)                                                            \
  uint32_t vpx_variance##W##x##H##_svp64(const uint8_t *src_ptr, int src_stride, \
                                     const uint8_t *ref_ptr, int ref_stride, \
                                     uint32_t *sse) {                        \
    int sum;                                                                 \
    variance_svp64(src_ptr, src_stride, ref_ptr, ref_stride, W, H, sse, &sum); \
    return *sse - (uint32_t)(((int64_t)sum * sum) / (W * H));                \
  }

/* Identical to the variance call except it takes an additional parameter, sum,
 * and returns that value using pass-by-reference instead of returning
 * sse - sum^2 / w*h
 */
#define GET_VAR(W, H)                                                   \
  void vpx_get##W##x##H##var_svp64(const uint8_t *src_ptr, int src_stride,  \
                               const uint8_t *ref_ptr, int ref_stride,  \
                               uint32_t *sse, int *sum) {               \
    variance_svp64(src_ptr, src_stride, ref_ptr, ref_stride, W, H, sse, sum); \
  }

/* Identical to the variance call except it does not calculate the
 * sse - sum^2 / w*h and returns sse in addtion to modifying the passed in
 * variable.
 */
#define MSE(W, H)                                                        \
  uint32_t vpx_mse##W##x##H##_svp64(const uint8_t *src_ptr, int src_stride,  \
                                const uint8_t *ref_ptr, int ref_stride,  \
                                uint32_t *sse) {                         \
    int sum;                                                             \
    variance_svp64(src_ptr, src_stride, ref_ptr, ref_stride, W, H, sse, &sum); \
    return *sse;                                                         \
  }

/* All three forms of the variance are available in the same sizes. */
#define VARIANCES(W, H) \
  VAR(W, H) 

VARIANCES(32, 32)
VARIANCES(32, 16)
VARIANCES(16, 32)
VARIANCES(16, 16)
VARIANCES(16, 8)
VARIANCES(8, 16)
VARIANCES(8, 8)
VARIANCES(8, 4)
VARIANCES(4, 8)
VARIANCES(4, 4)

GET_VAR(16, 16)
GET_VAR(8, 8)

MSE(16, 16)
MSE(16, 8)
MSE(8, 16)
MSE(8, 8)



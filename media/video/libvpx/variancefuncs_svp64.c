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

#define DECLARE_ALIGNED(n, typ, val) typ val __attribute__((aligned(n)))

#define ROUND_POWER_OF_TWO(value, n) (((value) + (1 << ((n)-1))) >> (n))

#define FILTER_BITS 7

static const uint8_t bilinear_filters[8][2] = {
  { 128, 0 }, { 112, 16 }, { 96, 32 }, { 80, 48 },
  { 64, 64 }, { 48, 80 },  { 32, 96 }, { 16, 112 },
};

// Applies a 1-D 2-tap bilinear filter to the source block in either horizontal
// or vertical direction to produce the filtered output block. Used to implement
// the first-pass of 2-D separable filter.
//
// Produces int16_t output to retain precision for the next pass. Two filter
// taps should sum to FILTER_WEIGHT. pixel_step defines whether the filter is
// applied horizontally (pixel_step = 1) or vertically (pixel_step = stride).
// It defines the offset required to move from one input to the next.
static void var_filter_block2d_bil_first_pass_svp64(
    const uint8_t *src_ptr, uint16_t *ref_ptr, unsigned int src_pixels_per_line,
    int pixel_step, unsigned int output_height, unsigned int output_width,
    const uint8_t *filter) {
  unsigned int i, j;

  for (i = 0; i < output_height; ++i) {
    for (j = 0; j < output_width; ++j) {
      ref_ptr[j] = ROUND_POWER_OF_TWO(
          (int)src_ptr[0] * filter[0] + (int)src_ptr[pixel_step] * filter[1],
          FILTER_BITS);

      ++src_ptr;
    }

    src_ptr += src_pixels_per_line - output_width;
    ref_ptr += output_width;
  }
}

// Applies a 1-D 2-tap bilinear filter to the source block in either horizontal
// or vertical direction to produce the filtered output block. Used to implement
// the second-pass of 2-D separable filter.
//
// Requires 16-bit input as produced by filter_block2d_bil_first_pass. Two
// filter taps should sum to FILTER_WEIGHT. pixel_step defines whether the
// filter is applied horizontally (pixel_step = 1) or vertically
// (pixel_step = stride). It defines the offset required to move from one input
// to the next. Output is 8-bit.
static void var_filter_block2d_bil_second_pass_svp64(
    const uint16_t *src_ptr, uint8_t *ref_ptr, unsigned int src_pixels_per_line,
    unsigned int pixel_step, unsigned int output_height,
    unsigned int output_width, const uint8_t *filter) {
  unsigned int i, j;

  for (i = 0; i < output_height; ++i) {
    for (j = 0; j < output_width; ++j) {
      ref_ptr[j] = ROUND_POWER_OF_TWO(
          (int)src_ptr[0] * filter[0] + (int)src_ptr[pixel_step] * filter[1],
          FILTER_BITS);
      ++src_ptr;
    }

    src_ptr += src_pixels_per_line - output_width;
    ref_ptr += output_width;
  }
}

void vpx_comp_avg_pred_svp64(uint8_t *comp_pred, const uint8_t *pred, int width,
                         int height, const uint8_t *ref, int ref_stride) {
  int i, j;

  for (i = 0; i < height; ++i) {
    for (j = 0; j < width; ++j) {
      const int tmp = pred[j] + ref[j];
      comp_pred[j] = ROUND_POWER_OF_TWO(tmp, 1);
    }
    comp_pred += width;
    pred += width;
    ref += ref_stride;
  }
}

#define VAR(W, H)                                                            \
  uint32_t vpx_variance##W##x##H##_svp64(const uint8_t *src_ptr, int src_stride, \
                                     const uint8_t *ref_ptr, int ref_stride, \
                                     uint32_t *sse) {                        \
    int sum;                                                                 \
    variance_svp64(src_ptr, src_stride, ref_ptr, ref_stride, W, H, sse, &sum); \
    return *sse - (uint32_t)(((int64_t)sum * sum) / (W * H));                \
  }

#define SUBPIX_VAR(W, H)                                                     \
  uint32_t vpx_sub_pixel_variance##W##x##H##_svp64(                          \
      const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset,    \
      const uint8_t *ref_ptr, int ref_stride, uint32_t *sse) {               \
    uint16_t fdata3[(H + 1) * W];                                            \
    uint8_t temp2[H * W];                                                    \
                                                                             \
    var_filter_block2d_bil_first_pass_svp64(src_ptr, fdata3, src_stride, 1, H + 1, \
                                      W, bilinear_filters[x_offset]);        \
    var_filter_block2d_bil_second_pass_svp64(fdata3, temp2, W, W, H, W,      \
                                       bilinear_filters[y_offset]);          \
                                                                             \
    return vpx_variance##W##x##H##_svp64(temp2, W, ref_ptr, ref_stride, sse);\
  }

#define SUBPIX_AVG_VAR(W, H)                                                 \
  uint32_t vpx_sub_pixel_avg_variance##W##x##H##_svp64(                      \
      const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset,    \
      const uint8_t *ref_ptr, int ref_stride, uint32_t *sse,                 \
      const uint8_t *second_pred) {                                          \
    uint16_t fdata3[(H + 1) * W];                                            \
    uint8_t temp2[H * W];                                                    \
    DECLARE_ALIGNED(16, uint8_t, temp3[H * W]);                              \
                                                                             \
    var_filter_block2d_bil_first_pass_svp64(src_ptr, fdata3, src_stride, 1, H + 1, \
                                      W, bilinear_filters[x_offset]);        \
    var_filter_block2d_bil_second_pass_svp64(fdata3, temp2, W, W, H, W,      \
                                       bilinear_filters[y_offset]);          \
                                                                             \
    vpx_comp_avg_pred_svp64(temp3, second_pred, W, H, temp2, W);             \
                                                                             \
    return vpx_variance##W##x##H##_svp64(temp3, W, ref_ptr, ref_stride, sse);\
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
  VAR(W, H)             \
  SUBPIX_VAR(W, H)      \
  SUBPIX_AVG_VAR(W, H)

VARIANCES(64, 64)
VARIANCES(64, 32)
VARIANCES(32, 64)
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



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

uint32_t vpx_get4x4sse_cs_c(const uint8_t *src_ptr, int src_stride,
                            const uint8_t *ref_ptr, int ref_stride);

uint32_t vpx_get_mb_ss_c(const int16_t *src_ptr);

void variance_c(const uint8_t *src_ptr, int src_stride,
                const uint8_t *ref_ptr, int ref_stride, int w, int h,
                uint32_t *sse, int *sum);

void var_filter_block2d_bil_first_pass_c(
    const uint8_t *src_ptr, uint16_t *ref_ptr, unsigned int src_pixels_per_line,
    int pixel_step, unsigned int output_height, unsigned int output_width,
    const uint8_t *filter);

void var_filter_block2d_bil_second_pass_c(
    const uint16_t *src_ptr, uint8_t *ref_ptr, unsigned int src_pixels_per_line,
    unsigned int pixel_step, unsigned int output_height,
    unsigned int output_width, const uint8_t *filter);

void vpx_comp_avg_pred_c(uint8_t *comp_pred, const uint8_t *pred, int width,
                         int height, const uint8_t *ref, int ref_stride);


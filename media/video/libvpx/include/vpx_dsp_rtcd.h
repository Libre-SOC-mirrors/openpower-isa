// This file is generated. Do not edit.
#ifndef VPX_DSP_RTCD_H_
#define VPX_DSP_RTCD_H_

#ifdef RTCD_C
#define RTCD_EXTERN
#else
#define RTCD_EXTERN extern
#endif

/*
 * DSP
 */

#include "vpx_integer.h"

#ifdef __cplusplus
extern "C" {
#endif

unsigned int vpx_get_mb_ss_c(const int16_t *);

unsigned int vpx_get4x4sse_cs_c(const unsigned char *src_ptr, int src_stride, const unsigned char *ref_ptr, int ref_stride);

void vpx_comp_avg_pred_c(uint8_t *comp_pred, const uint8_t *pred, int width, int height, const uint8_t *ref, int ref_stride);

unsigned int vpx_mse16x16_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_mse16x8_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_mse8x16_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_mse8x8_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

uint32_t vpx_sub_pixel_avg_variance16x16_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance16x32_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance16x8_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance32x16_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance32x32_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance32x64_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance4x4_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance4x8_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance64x32_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance64x64_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance8x16_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance8x4_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance8x8_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_variance16x16_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance16x32_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance16x8_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance32x16_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance32x32_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance32x64_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance4x4_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance4x8_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance64x32_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance64x64_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance8x16_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance8x4_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance8x8_c(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

unsigned int vpx_variance16x16_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance16x32_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance16x8_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance32x16_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance32x32_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance32x64_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance4x4_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance4x8_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance64x32_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance64x64_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance8x16_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance8x4_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance8x8_c(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);


// SVP64 prototypes
unsigned int vpx_get_mb_ss_svp64(const int16_t *);

unsigned int vpx_get4x4sse_cs_svp64(const unsigned char *src_ptr, int src_stride, const unsigned char *ref_ptr, int ref_stride);

void vpx_comp_avg_pred_svp64(uint8_t *comp_pred, const uint8_t *pred, int width, int height, const uint8_t *ref, int ref_stride);

unsigned int vpx_mse16x16_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_mse16x8_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_mse8x16_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_mse8x8_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

uint32_t vpx_sub_pixel_avg_variance16x16_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance16x32_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance16x8_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance32x16_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance32x32_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance32x64_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance4x4_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance4x8_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance64x32_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance64x64_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance8x16_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance8x4_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_avg_variance8x8_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse, const uint8_t *second_pred);

uint32_t vpx_sub_pixel_variance16x16_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance16x32_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance16x8_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance32x16_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance32x32_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance32x64_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance4x4_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance4x8_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance64x32_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance64x64_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance8x16_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance8x4_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

uint32_t vpx_sub_pixel_variance8x8_svp64(const uint8_t *src_ptr, int src_stride, int x_offset, int y_offset, const uint8_t *ref_ptr, int ref_stride, uint32_t *sse);

unsigned int vpx_variance16x16_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance16x32_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance16x8_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance32x16_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance32x32_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance32x64_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance4x4_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance4x8_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance64x32_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance64x64_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance8x16_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance8x4_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

unsigned int vpx_variance8x8_svp64(const uint8_t *src_ptr, int src_stride, const uint8_t *ref_ptr, int ref_stride, unsigned int *sse);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif

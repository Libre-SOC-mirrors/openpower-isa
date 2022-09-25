/*
 *  Copyright (c) 2012 The WebM project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include <cstdlib>
#include <new>

#include <gtest/gtest.h>

#include "vpx_misc.h"
#include "vpx_dsp_rtcd.h"
#include "acm_random.h"
#include "clear_system_state.h"
#include "register_state_check.h"
#include "vpx_integer.h"
#include "variance.h"
#include "vpx_mem.h"
#include "mem.h"
#include "vpx_timer.h"

namespace {

typedef unsigned int (*Get4x4SseFunc)(const uint8_t *a, int a_stride,
                                      const uint8_t *b, int b_stride);
typedef unsigned int (*SumOfSquaresFunction)(const int16_t *src);

using libvpx_test::ACMRandom;

// Truncate high bit depth results by downshifting (with rounding) by:
// 2 * (bit_depth - 8) for sse
// (bit_depth - 8) for se
static void RoundHighBitDepth(int bit_depth, int64_t *se, uint64_t *sse) {
  switch (bit_depth) {
    case VPX_BITS_12:
      *sse = (*sse + 128) >> 8;
      *se = (*se + 8) >> 4;
      break;
    case VPX_BITS_10:
      *sse = (*sse + 8) >> 4;
      *se = (*se + 2) >> 2;
      break;
    case VPX_BITS_8:
    default: break;
  }
}

static unsigned int mb_ss_ref(const int16_t *src) {
  unsigned int res = 0;
  for (int i = 0; i < 256; ++i) {
    res += src[i] * src[i];
  }
  return res;
}

/* Note:
 *  Our codebase calculates the "diff" value in the variance algorithm by
 *  (src - ref).
 */
static uint32_t variance_ref(const uint8_t *src, const uint8_t *ref, int l2w,
                             int l2h, int src_stride, int ref_stride,
                             uint32_t *sse_ptr, bool use_high_bit_depth_,
                             vpx_bit_depth_t bit_depth) {
  int64_t se = 0;
  uint64_t sse = 0;
  const int w = 1 << l2w;
  const int h = 1 << l2h;
  for (int y = 0; y < h; y++) {
    for (int x = 0; x < w; x++) {
      int diff;
      if (!use_high_bit_depth_) {
        diff = src[y * src_stride + x] - ref[y * ref_stride + x];
        se += diff;
        sse += diff * diff;
      }
    }
  }
  RoundHighBitDepth(bit_depth, &se, &sse);
  *sse_ptr = static_cast<uint32_t>(sse);
  return static_cast<uint32_t>(
      sse - ((static_cast<int64_t>(se) * se) >> (l2w + l2h)));
}

/* The subpel reference functions differ from the codec version in one aspect:
 * they calculate the bilinear factors directly instead of using a lookup table
 * and therefore upshift xoff and yoff by 1. Only every other calculated value
 * is used so the codec version shrinks the table to save space and maintain
 * compatibility with vp8.
 */
static uint32_t subpel_variance_ref(const uint8_t *ref, const uint8_t *src,
                                    int l2w, int l2h, int xoff, int yoff,
                                    uint32_t *sse_ptr, bool use_high_bit_depth_,
                                    vpx_bit_depth_t bit_depth) {
  int64_t se = 0;
  uint64_t sse = 0;
  const int w = 1 << l2w;
  const int h = 1 << l2h;

  xoff <<= 1;
  yoff <<= 1;

  for (int y = 0; y < h; y++) {
    for (int x = 0; x < w; x++) {
      // Bilinear interpolation at a 16th pel step.
      if (!use_high_bit_depth_) {
        const int a1 = ref[(w + 1) * (y + 0) + x + 0];
        const int a2 = ref[(w + 1) * (y + 0) + x + 1];
        const int b1 = ref[(w + 1) * (y + 1) + x + 0];
        const int b2 = ref[(w + 1) * (y + 1) + x + 1];
        const int a = a1 + (((a2 - a1) * xoff + 8) >> 4);
        const int b = b1 + (((b2 - b1) * xoff + 8) >> 4);
        const int r = a + (((b - a) * yoff + 8) >> 4);
        const int diff = r - src[w * y + x];
        se += diff;
        sse += diff * diff;
      }
    }
  }
  RoundHighBitDepth(bit_depth, &se, &sse);
  *sse_ptr = static_cast<uint32_t>(sse);
  return static_cast<uint32_t>(
      sse - ((static_cast<int64_t>(se) * se) >> (l2w + l2h)));
}

static uint32_t subpel_avg_variance_ref(const uint8_t *ref, const uint8_t *src,
                                        const uint8_t *second_pred, int l2w,
                                        int l2h, int xoff, int yoff,
                                        uint32_t *sse_ptr,
                                        bool use_high_bit_depth,
                                        vpx_bit_depth_t bit_depth) {
  int64_t se = 0;
  uint64_t sse = 0;
  const int w = 1 << l2w;
  const int h = 1 << l2h;

  xoff <<= 1;
  yoff <<= 1;

  for (int y = 0; y < h; y++) {
    for (int x = 0; x < w; x++) {
      // bilinear interpolation at a 16th pel step
      if (!use_high_bit_depth) {
        const int a1 = ref[(w + 1) * (y + 0) + x + 0];
        const int a2 = ref[(w + 1) * (y + 0) + x + 1];
        const int b1 = ref[(w + 1) * (y + 1) + x + 0];
        const int b2 = ref[(w + 1) * (y + 1) + x + 1];
        const int a = a1 + (((a2 - a1) * xoff + 8) >> 4);
        const int b = b1 + (((b2 - b1) * xoff + 8) >> 4);
        const int r = a + (((b - a) * yoff + 8) >> 4);
        const int diff =
            ((r + second_pred[w * y + x] + 1) >> 1) - src[w * y + x];
        se += diff;
        sse += diff * diff;
      }
    }
  }
  RoundHighBitDepth(bit_depth, &se, &sse);
  *sse_ptr = static_cast<uint32_t>(sse);
  return static_cast<uint32_t>(
      sse - ((static_cast<int64_t>(se) * se) >> (l2w + l2h)));
}

////////////////////////////////////////////////////////////////////////////////

class SumOfSquaresTest : public ::testing::TestWithParam<SumOfSquaresFunction> {
 public:
  SumOfSquaresTest() : func_(GetParam()) {}

  virtual ~SumOfSquaresTest() { libvpx_test::ClearSystemState(); }

 protected:
  void ConstTest();
  void RefTest();

  SumOfSquaresFunction func_;
  ACMRandom rnd_;
};

void SumOfSquaresTest::ConstTest() {
  int16_t mem[256];
  unsigned int res;
  for (int v = 0; v < 5; ++v) {
    for (int i = 0; i < 256; ++i) {
      mem[i] = v;
    }
    ASM_REGISTER_STATE_CHECK(res = func_(mem));
    EXPECT_EQ(256u * (v * v), res);
  }
}

void SumOfSquaresTest::RefTest() {
  int16_t mem[256];
  for (int i = 0; i < 5; ++i) {
    for (int j = 0; j < 256; ++j) {
      mem[j] = rnd_.Rand8() - rnd_.Rand8();
    }

    const unsigned int expected = mb_ss_ref(mem);
    unsigned int res;
    ASM_REGISTER_STATE_CHECK(res = func_(mem));
    EXPECT_EQ(expected, res);
  }
}

////////////////////////////////////////////////////////////////////////////////
// Encapsulating struct to store the function to test along with
// some testing context.
// Can be used for MSE, SSE, Variance, etc.

template <typename Func>
struct TestParams {
  TestParams(int log2w = 0, int log2h = 0, Func function = nullptr,
             int bit_depth_value = 0)
      : log2width(log2w), log2height(log2h), func(function) {
    use_high_bit_depth = (bit_depth_value > 0);
    if (use_high_bit_depth) {
      bit_depth = static_cast<vpx_bit_depth_t>(bit_depth_value);
    } else {
      bit_depth = VPX_BITS_8;
    }
    width = 1 << log2width;
    height = 1 << log2height;
    block_size = width * height;
    mask = (1u << bit_depth) - 1;
  }

  int log2width, log2height;
  int width, height;
  int block_size;
  Func func;
  vpx_bit_depth_t bit_depth;
  bool use_high_bit_depth;
  uint32_t mask;
};

template <typename Func>
std::ostream &operator<<(std::ostream &os, const TestParams<Func> &p) {
  return os << "log2width/height:" << p.log2width << "/" << p.log2height
            << " function:" << reinterpret_cast<const void *>(p.func)
            << " bit-depth:" << p.bit_depth;
}

// Main class for testing a function type
template <typename FunctionType>
class MainTestClass
    : public ::testing::TestWithParam<TestParams<FunctionType> > {
 public:
  virtual void SetUp() {
    params_ = this->GetParam();

    rnd_.Reset(ACMRandom::DeterministicSeed());
    const size_t unit =
        use_high_bit_depth() ? sizeof(uint16_t) : sizeof(uint8_t);
    src_ = reinterpret_cast<uint8_t *>(vpx_memalign(16, block_size() * unit));
    ref_ = new uint8_t[block_size() * unit];
    ASSERT_NE(src_, nullptr);
    ASSERT_NE(ref_, nullptr);
  }

  virtual void TearDown() {

    vpx_free(src_);
    delete[] ref_;
    src_ = nullptr;
    ref_ = nullptr;
    libvpx_test::ClearSystemState();
  }

 protected:
  // We could sub-class MainTestClass into dedicated class for Variance
  // and MSE/SSE, but it involves a lot of 'this->xxx' dereferencing
  // to access top class fields xxx. That's cumbersome, so for now we'll just
  // implement the testing methods here:

  // Variance tests
  void ZeroTest();
  void RefTest();
  void RefStrideTest();
  void OneQuarterTest();
  void SpeedTest();

  // MSE/SSE tests
  void RefTestMse();
  void RefTestSse();
  void MaxTestMse();
  void MaxTestSse();

 protected:
  ACMRandom rnd_;
  uint8_t *src_;
  uint8_t *ref_;
  TestParams<FunctionType> params_;

  // some relay helpers
  bool use_high_bit_depth() const { return params_.use_high_bit_depth; }
  int byte_shift() const { return params_.bit_depth - 8; }
  int block_size() const { return params_.block_size; }
  int width() const { return params_.width; }
  int height() const { return params_.height; }
  uint32_t mask() const { return params_.mask; }
};

////////////////////////////////////////////////////////////////////////////////
// Tests related to variance.

template <typename VarianceFunctionType>
void MainTestClass<VarianceFunctionType>::ZeroTest() {
  for (int i = 0; i <= 1; ++i) {
    if (!use_high_bit_depth()) {
      memset(src_, i, block_size());
    } else {
      uint16_t *const src16 = CONVERT_TO_SHORTPTR(src_);
      for (int k = 0; k < block_size(); ++k) src16[k] = i << byte_shift();
    }
    for (int j = 0; j <= 1; ++j) {
      if (!use_high_bit_depth()) {
        memset(ref_, j, block_size());
      } else {
        uint16_t *const ref16 = CONVERT_TO_SHORTPTR(ref_);
        for (int k = 0; k < block_size(); ++k) ref16[k] = j << byte_shift();
      }
      unsigned int sse, var;
      ASM_REGISTER_STATE_CHECK(
          var = params_.func(src_, width(), ref_, width(), &sse));
      EXPECT_EQ(0u, var) << "src values: " << i << " ref values: " << j;
    }
  }
}

template <typename VarianceFunctionType>
void MainTestClass<VarianceFunctionType>::RefTest() {
  for (int i = 0; i < 3; ++i) {
    for (int j = 0; j < block_size(); j++) {
      if (!use_high_bit_depth()) {
        src_[j] = rnd_.Rand8();
        ref_[j] = rnd_.Rand8();
      }
    }
    unsigned int sse1, sse2, var1, var2;
    const int stride = width();
    ASM_REGISTER_STATE_CHECK(
        var1 = params_.func(src_, stride, ref_, stride, &sse1));
    var2 =
        variance_ref(src_, ref_, params_.log2width, params_.log2height, stride,
                     stride, &sse2, use_high_bit_depth(), params_.bit_depth);
    EXPECT_EQ(sse1, sse2) << "Error at test index: " << i;
    EXPECT_EQ(var1, var2) << "Error at test index: " << i;
  }
}

template <typename VarianceFunctionType>
void MainTestClass<VarianceFunctionType>::RefStrideTest() {
  for (int i = 0; i < 3; ++i) {
    const int ref_stride = (i & 1) * width();
    const int src_stride = ((i >> 1) & 1) * width();
    for (int j = 0; j < block_size(); j++) {
      const int ref_ind = (j / width()) * ref_stride + j % width();
      const int src_ind = (j / width()) * src_stride + j % width();
      if (!use_high_bit_depth()) {
        src_[src_ind] = rnd_.Rand8();
        ref_[ref_ind] = rnd_.Rand8();
      }
    }
    unsigned int sse1, sse2;
    unsigned int var1, var2;

    ASM_REGISTER_STATE_CHECK(
        var1 = params_.func(src_, src_stride, ref_, ref_stride, &sse1));
    var2 = variance_ref(src_, ref_, params_.log2width, params_.log2height,
                        src_stride, ref_stride, &sse2, use_high_bit_depth(),
                        params_.bit_depth);
    EXPECT_EQ(sse1, sse2) << "Error at test index: " << i;
    EXPECT_EQ(var1, var2) << "Error at test index: " << i;
  }
}

template <typename VarianceFunctionType>
void MainTestClass<VarianceFunctionType>::OneQuarterTest() {
  const int half = block_size() / 2;
  if (!use_high_bit_depth()) {
    memset(src_, 255, block_size());
    memset(ref_, 255, half);
    memset(ref_ + half, 0, half);
  }
  unsigned int sse, var, expected;
  ASM_REGISTER_STATE_CHECK(
      var = params_.func(src_, width(), ref_, width(), &sse));
  expected = block_size() * 255 * 255 / 4;
  EXPECT_EQ(expected, var);
}

template <typename VarianceFunctionType>
void MainTestClass<VarianceFunctionType>::SpeedTest() {
  const int half = block_size() / 2;
  if (!use_high_bit_depth()) {
    memset(src_, 255, block_size());
    memset(ref_, 255, half);
    memset(ref_ + half, 0, half);
  }
  unsigned int sse;

  vpx_usec_timer timer;
  vpx_usec_timer_start(&timer);
  for (int i = 0; i < (1 << 30) / block_size(); ++i) {
    const uint32_t variance = params_.func(src_, width(), ref_, width(), &sse);
    // Ignore return value.
    (void)variance;
  }
  vpx_usec_timer_mark(&timer);
  const int elapsed_time = static_cast<int>(vpx_usec_timer_elapsed(&timer));
  printf("Variance %dx%d time: %5d ms\n", width(), height(),
         elapsed_time / 1000);
}

////////////////////////////////////////////////////////////////////////////////
// Tests related to MSE / SSE.

template <typename FunctionType>
void MainTestClass<FunctionType>::RefTestMse() {
  for (int i = 0; i < 3; ++i) {
    for (int j = 0; j < block_size(); ++j) {
      src_[j] = rnd_.Rand8();
      ref_[j] = rnd_.Rand8();
    }
    unsigned int sse1, sse2;
    const int stride = width();
    ASM_REGISTER_STATE_CHECK(params_.func(src_, stride, ref_, stride, &sse1));
    variance_ref(src_, ref_, params_.log2width, params_.log2height, stride,
                 stride, &sse2, false, VPX_BITS_8);
    EXPECT_EQ(sse1, sse2);
  }
}

template <typename FunctionType>
void MainTestClass<FunctionType>::RefTestSse() {
  for (int i = 0; i < 3; ++i) {
    for (int j = 0; j < block_size(); ++j) {
      src_[j] = rnd_.Rand8();
      ref_[j] = rnd_.Rand8();
    }
    unsigned int sse2;
    unsigned int var1;
    const int stride = width();
    ASM_REGISTER_STATE_CHECK(var1 = params_.func(src_, stride, ref_, stride));
    variance_ref(src_, ref_, params_.log2width, params_.log2height, stride,
                 stride, &sse2, false, VPX_BITS_8);
    EXPECT_EQ(var1, sse2);
  }
}

template <typename FunctionType>
void MainTestClass<FunctionType>::MaxTestMse() {
  memset(src_, 255, block_size());
  memset(ref_, 0, block_size());
  unsigned int sse;
  ASM_REGISTER_STATE_CHECK(params_.func(src_, width(), ref_, width(), &sse));
  const unsigned int expected = block_size() * 255 * 255;
  EXPECT_EQ(expected, sse);
}

template <typename FunctionType>
void MainTestClass<FunctionType>::MaxTestSse() {
  memset(src_, 255, block_size());
  memset(ref_, 0, block_size());
  unsigned int var;
  ASM_REGISTER_STATE_CHECK(var = params_.func(src_, width(), ref_, width()));
  const unsigned int expected = block_size() * 255 * 255;
  EXPECT_EQ(expected, var);
}

////////////////////////////////////////////////////////////////////////////////

typedef MainTestClass<Get4x4SseFunc> VpxSseTest;
typedef MainTestClass<vpx_variance_fn_t> VpxMseTest;
typedef MainTestClass<vpx_variance_fn_t> VpxVarianceTest;

TEST_P(VpxSseTest, RefSse) { RefTestSse(); }
TEST_P(VpxSseTest, MaxSse) { MaxTestSse(); }
TEST_P(VpxMseTest, RefMse) { RefTestMse(); }
TEST_P(VpxMseTest, MaxMse) { MaxTestMse(); }
TEST_P(VpxVarianceTest, Zero) { ZeroTest(); }
TEST_P(VpxVarianceTest, Ref) { RefTest(); }
TEST_P(VpxVarianceTest, RefStride) { RefStrideTest(); }
TEST_P(VpxVarianceTest, OneQuarter) { OneQuarterTest(); }
TEST_P(SumOfSquaresTest, Const) { ConstTest(); }
TEST_P(SumOfSquaresTest, Ref) { RefTest(); }

INSTANTIATE_TEST_SUITE_P(C, SumOfSquaresTest,
                         ::testing::Values(vpx_get_mb_ss_c));

typedef TestParams<Get4x4SseFunc> SseParams;
INSTANTIATE_TEST_SUITE_P(C, VpxSseTest,
                         ::testing::Values(SseParams(2, 2,
                                                     &vpx_get4x4sse_cs_c)));

typedef TestParams<vpx_variance_fn_t> MseParams;
INSTANTIATE_TEST_SUITE_P(C, VpxMseTest,
                         ::testing::Values(MseParams(4, 4, &vpx_mse16x16_c),
                                           MseParams(4, 3, &vpx_mse16x8_c),
                                           MseParams(3, 4, &vpx_mse8x16_c),
                                           MseParams(3, 3, &vpx_mse8x8_c)));

typedef TestParams<vpx_variance_fn_t> VarianceParams;
INSTANTIATE_TEST_SUITE_P(
    C, VpxVarianceTest,
    ::testing::Values(VarianceParams(5, 5, &vpx_variance32x32_c),
                      VarianceParams(5, 4, &vpx_variance32x16_c),
                      VarianceParams(4, 5, &vpx_variance16x32_c),
                      VarianceParams(4, 4, &vpx_variance16x16_c),
                      VarianceParams(4, 3, &vpx_variance16x8_c),
                      VarianceParams(3, 4, &vpx_variance8x16_c),
                      VarianceParams(3, 3, &vpx_variance8x8_c),
                      VarianceParams(3, 2, &vpx_variance8x4_c),
                      VarianceParams(2, 3, &vpx_variance4x8_c),
                      VarianceParams(2, 2, &vpx_variance4x4_c)));

INSTANTIATE_TEST_SUITE_P(SVP64, SumOfSquaresTest,
                         ::testing::Values(vpx_get_mb_ss_svp64));

typedef TestParams<Get4x4SseFunc> SseParams;
INSTANTIATE_TEST_SUITE_P(SVP64, VpxSseTest,
                         ::testing::Values(SseParams(2, 2,
                                                     &vpx_get4x4sse_cs_svp64)));

typedef TestParams<vpx_variance_fn_t> MseParams;
INSTANTIATE_TEST_SUITE_P(SVP64, VpxMseTest,
                         ::testing::Values(MseParams(4, 4, &vpx_mse16x16_svp64),
                                           MseParams(4, 3, &vpx_mse16x8_svp64),
                                           MseParams(3, 4, &vpx_mse8x16_svp64),
                                           MseParams(3, 3, &vpx_mse8x8_svp64)));

typedef TestParams<vpx_variance_fn_t> VarianceParams;
INSTANTIATE_TEST_SUITE_P(
    SVP64, VpxVarianceTest,
    ::testing::Values(VarianceParams(5, 5, &vpx_variance32x32_svp64),
                      VarianceParams(5, 4, &vpx_variance32x16_svp64),
                      VarianceParams(4, 5, &vpx_variance16x32_svp64),
                      VarianceParams(4, 4, &vpx_variance16x16_svp64),
                      VarianceParams(4, 3, &vpx_variance16x8_svp64),
                      VarianceParams(3, 4, &vpx_variance8x16_svp64),
                      VarianceParams(3, 3, &vpx_variance8x8_svp64),
                      VarianceParams(3, 2, &vpx_variance8x4_svp64),
                      VarianceParams(2, 3, &vpx_variance4x8_svp64),
                      VarianceParams(2, 2, &vpx_variance4x4_svp64)));

}  // namespace

/*
 * Copyright (c) 2001, 2002 Fabrice Bellard
 *
 * This file is part of FFmpeg.
 *
 * FFmpeg is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * FFmpeg is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with FFmpeg; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

#include <stdint.h>
#include <stddef.h>

#define USE_FLOATS 1
#define SBLIMIT 32
#define MDCT_BUF_SIZE 40

#define RENAME(n) n##_float

static inline float round_sample(float *sum)
{
    float sum1=*sum;
    *sum = 0;
    return sum1;
}

#define MACS(rt, ra, rb) rt+=(ra)*(rb)
#define MULS(ra, rb) ((ra)*(rb))
#define MULH3(x, y, s) ((s)*(y)*(x))
#define MLSS(rt, ra, rb) rt-=(ra)*(rb)
#define MULLx(x, y, s) ((y)*(x))
#define FIXHR(x)        ((float)(x))
#define FIXR(x)        ((float)(x))
#define SHR(a,b)       ((a)*(1.0f/(1<<(b))))

/* cos(pi*i/18) */
#define C1 FIXHR(0.98480775301220805936/2)
#define C2 FIXHR(0.93969262078590838405/2)
#define C3 FIXHR(0.86602540378443864676/2)
#define C4 FIXHR(0.76604444311897803520/2)
#define C5 FIXHR(0.64278760968653932632/2)
#define C6 FIXHR(0.5/2)
#define C7 FIXHR(0.34202014332566873304/2)
#define C8 FIXHR(0.17364817766693034885/2)

/* 0.5 / cos(pi*(2*i+1)/36) */
static const float icos36[9] = {
    FIXR(0.50190991877167369479),
    FIXR(0.51763809020504152469), //0
    FIXR(0.55168895948124587824),
    FIXR(0.61038729438072803416),
    FIXR(0.70710678118654752439), //1
    FIXR(0.87172339781054900991),
    FIXR(1.18310079157624925896),
    FIXR(1.93185165257813657349), //2
    FIXR(5.73685662283492756461),
};

/* 0.5 / cos(pi*(2*i+1)/36) */
static const float icos36h[9] = {
    FIXHR(0.50190991877167369479/2),
    FIXHR(0.51763809020504152469/2), //0
    FIXHR(0.55168895948124587824/2),
    FIXHR(0.61038729438072803416/2),
    FIXHR(0.70710678118654752439/2), //1
    FIXHR(0.87172339781054900991/2),
    FIXHR(1.18310079157624925896/4),
    FIXHR(1.93185165257813657349/4), //2
//    FIXHR(5.73685662283492756461),
};

/* using Lee like decomposition followed by hand coded 9 points DCT */
void imdct36(float *out, float *buf, float *in, const float *win)
{
    int i, j;
    float t0, t1, t2, t3, s0, s1, s2, s3;
    float tmp[18], *tmp1, *in1;

    for (i = 17; i >= 1; i--)
        in[i] += in[i-1];
    for (i = 17; i >= 3; i -= 2)
        in[i] += in[i-2];

    for (j = 0; j < 2; j++) {
        tmp1 = tmp + j;
        in1 = in + j;

        t2 = in1[2*4] + in1[2*8] - in1[2*2];

        t3 = in1[2*0] + SHR(in1[2*6],1);
        t1 = in1[2*0] - in1[2*6];
        tmp1[ 6] = t1 - SHR(t2,1);
        tmp1[16] = t1 + t2;

        t0 = MULH3(in1[2*2] + in1[2*4] ,    C2, 2);
        t1 = MULH3(in1[2*4] - in1[2*8] , -2*C8, 1);
        t2 = MULH3(in1[2*2] + in1[2*8] ,   -C4, 2);

        tmp1[10] = t3 - t0 - t2;
        tmp1[ 2] = t3 + t0 + t1;
        tmp1[14] = t3 + t2 - t1;

        tmp1[ 4] = MULH3(in1[2*5] + in1[2*7] - in1[2*1], -C3, 2);
        t2 = MULH3(in1[2*1] + in1[2*5],    C1, 2);
        t3 = MULH3(in1[2*5] - in1[2*7], -2*C7, 1);
        t0 = MULH3(in1[2*3], C3, 2);

        t1 = MULH3(in1[2*1] + in1[2*7],   -C5, 2);

        tmp1[ 0] = t2 + t3 + t0;
        tmp1[12] = t2 + t1 - t0;
        tmp1[ 8] = t3 - t1 - t0;
    }

    i = 0;
    for (j = 0; j < 4; j++) {
        t0 = tmp[i];
        t1 = tmp[i + 2];
        s0 = t1 + t0;
        s2 = t1 - t0;

        t2 = tmp[i + 1];
        t3 = tmp[i + 3];
        s1 = MULH3(t3 + t2, icos36h[    j], 2);
        s3 = MULLx(t3 - t2, icos36 [8 - j], FRAC_BITS);

        t0 = s0 + s1;
        t1 = s0 - s1;
        out[(9 + j) * SBLIMIT] = MULH3(t1, win[     9 + j], 1) + buf[4*(9 + j)];
        out[(8 - j) * SBLIMIT] = MULH3(t1, win[     8 - j], 1) + buf[4*(8 - j)];
        buf[4 * ( 9 + j     )] = MULH3(t0, win[MDCT_BUF_SIZE/2 + 9 + j], 1);
        buf[4 * ( 8 - j     )] = MULH3(t0, win[MDCT_BUF_SIZE/2 + 8 - j], 1);

        t0 = s2 + s3;
        t1 = s2 - s3;
        out[(9 + 8 - j) * SBLIMIT] = MULH3(t1, win[     9 + 8 - j], 1) + buf[4*(9 + 8 - j)];
        out[         j  * SBLIMIT] = MULH3(t1, win[             j], 1) + buf[4*(        j)];
        buf[4 * ( 9 + 8 - j     )] = MULH3(t0, win[MDCT_BUF_SIZE/2 + 9 + 8 - j], 1);
        buf[4 * (         j     )] = MULH3(t0, win[MDCT_BUF_SIZE/2         + j], 1);
        i += 4;
    }

    s0 = tmp[16];
    s1 = MULH3(tmp[17], icos36h[4], 2);
    t0 = s0 + s1;
    t1 = s0 - s1;
    out[(9 + 4) * SBLIMIT] = MULH3(t1, win[     9 + 4], 1) + buf[4*(9 + 4)];
    out[(8 - 4) * SBLIMIT] = MULH3(t1, win[     8 - 4], 1) + buf[4*(8 - 4)];
    buf[4 * ( 9 + 4     )] = MULH3(t0, win[MDCT_BUF_SIZE/2 + 9 + 4], 1);
    buf[4 * ( 8 - 4     )] = MULH3(t0, win[MDCT_BUF_SIZE/2 + 8 - 4], 1);
}

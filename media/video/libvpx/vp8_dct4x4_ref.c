/*
 *  Copyright (c) 2010 The WebM project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include <math.h>
#include <stdint.h>
#include <stdio.h>

#include "vp8_rtcd.h"

void vp8_short_fdct4x4_c(int16_t *input, int16_t *output, int32_t pitch) {
  int i;
  int a1, b1, c1, d1;
  short *ip = input;
  short *op = output;

  for (i = 0; i < 4; ++i) {
    a1 = ((ip[0] + ip[3]));
    b1 = ((ip[1] + ip[2]));
    c1 = ((ip[1] - ip[2]));
    d1 = ((ip[0] - ip[3]));

    a1 *= 8;
    b1 *= 8;
    c1 *= 8;
    d1 *= 8;
    //printf("a1 = %08x\tb1 = %08x\tc1 = %08x\td1 = %08x\n", a1, b1, c1, d1);

    op[0] = a1 + b1;
    op[2] = a1 - b1;
    //printf("op[0] = %04x\top[2] = %04x\n", (uint16_t)op[0], (uint16_t)op[2]);

    op[1] = (c1 * 2217 + d1 * 5352 + 14500) >> 12;
    op[3] = (d1 * 2217 - c1 * 5352 + 7500) >> 12;
    //printf("op[1] = %04x\top[3] = %04x\n", (uint16_t)op[1], (uint16_t)op[3]);

    ip += pitch / 2;
    op += 4;
  }
  ip = output;
  op = output;
  for (i = 0; i < 4; ++i) {
    a1 = ip[0] + ip[12];
    b1 = ip[4] + ip[8];
    c1 = ip[4] - ip[8];
    d1 = ip[0] - ip[12];
    //printf("a1 = %08x\tb1 = %08x\tc1 = %08x\td1 = %08x\n", a1, b1, c1, d1);

    op[0] = (a1 + b1 + 7) >> 4;
    op[8] = (a1 - b1 + 7) >> 4;
    //printf("op[%d] = %08x\top[%d] = %08x\n", i, op[0], i+8, op[8]);

    op[4] = ((c1 * 2217 + d1 * 5352 + 12000) >> 16) + (d1 != 0);
    op[12] = (d1 * 2217 - c1 * 5352 + 51000) >> 16;
    //printf("op[%d] = %04x\top[%d] = %04x\n", i+4, (uint16_t)op[4], i+12, (uint16_t)op[12]);

    ip++;
    op++;
  }
}

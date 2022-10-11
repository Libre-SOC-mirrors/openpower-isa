/*
 * Copyright © 2018, VideoLAN and dav1d authors
 * Copyright © 2018, Two Orioles, LLC
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
 * ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "config.h"

#include <stdlib.h>

#include "common/intops.h"

#include "src/ppc/cdef.h"
#include "src/tables.h"

int cdef_find_dir_svp64(const pixel *img, const ptrdiff_t stride,
                           unsigned *const var HIGHBD_DECL_SUFFIX)
{
    const int bitdepth_min_8 = bitdepth_from_max(bitdepth_max) - 8;
    int partial_sum_hv[2][8] = { { 0 } };
    int partial_sum_diag[2][15] = { { 0 } };
    int partial_sum_alt[4][11] = { { 0 } };

    for (int y = 0; y < 8; y++) {
        for (int x = 0; x < 8; x++) {
            const int px = (img[x] >> bitdepth_min_8) - 128;

            partial_sum_diag[0][     y       +  x      ] += px;
            partial_sum_alt [0][     y       + (x >> 1)] += px;
            partial_sum_hv  [0][     y                 ] += px;
            partial_sum_alt [1][3 +  y       - (x >> 1)] += px;
            partial_sum_diag[1][7 +  y       -  x      ] += px;
            partial_sum_alt [2][3 - (y >> 1) +  x      ] += px;
            partial_sum_hv  [1][                x      ] += px;
            partial_sum_alt [3][    (y >> 1) +  x      ] += px;
        }
        img += PXSTRIDE(stride);
    }

    unsigned cost[8] = { 0 };
/*    for (int n = 0; n < 8; n++) {
        cost[2] += partial_sum_hv[0][n] * partial_sum_hv[0][n];
        cost[6] += partial_sum_hv[1][n] * partial_sum_hv[1][n];
    }
    cost[2] *= 105;
    cost[6] *= 105;

    static const uint16_t div_table[7] = { 840, 420, 280, 210, 168, 140, 120 };
    for (int n = 0; n < 7; n++) {
        const int d = div_table[n];
        cost[0] += (partial_sum_diag[0][n]      * partial_sum_diag[0][n] +
                    partial_sum_diag[0][14 - n] * partial_sum_diag[0][14 - n]) * d;
        cost[4] += (partial_sum_diag[1][n]      * partial_sum_diag[1][n] +
                    partial_sum_diag[1][14 - n] * partial_sum_diag[1][14 - n]) * d;
    }
    cost[0] += partial_sum_diag[0][7] * partial_sum_diag[0][7] * 105;
    cost[4] += partial_sum_diag[1][7] * partial_sum_diag[1][7] * 105;

    for (int n = 0; n < 4; n++) {
        unsigned *const cost_ptr = &cost[n * 2 + 1];
        for (int m = 0; m < 5; m++)
            *cost_ptr += partial_sum_alt[n][3 + m] * partial_sum_alt[n][3 + m];
        *cost_ptr *= 105;
        for (int m = 0; m < 3; m++) {
            const int d = div_table[2 * m + 1];
            *cost_ptr += (partial_sum_alt[n][m]      * partial_sum_alt[n][m] +
                          partial_sum_alt[n][10 - m] * partial_sum_alt[n][10 - m]) * d;
        }
    }
*/
    int best_dir = 0;
    unsigned best_cost = cost[0];
    for (int n = 1; n < 8; n++) {
        if (cost[n] > best_cost) {
            best_cost = cost[n];
            best_dir = n;
        }
    }

    *var = (best_cost - (cost[best_dir ^ 4])) >> 10;
    return best_dir;
}

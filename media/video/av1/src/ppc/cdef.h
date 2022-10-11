/*
 * Copyright © 2019, Luca Barbato
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

#include <stdlib.h>

#include "common/bitdepth.h"
#include "common/intops.h"

#include "src/cdef.h"
#include "src/cpu.h"

/*
#define cdef_svp64_fn(w, h) \
void cdef_filter_block_##w##x##h##_svp64(pixel *const dst, \
                                       const ptrdiff_t dst_stride, \
                                       const pixel (*left)[2], \
                                       const pixel *const top, \
                                       const pixel *const bottom, \
                                       const int pri_strength, \
                                       const int sec_strength, \
                                       const int dir, \
                                       const int damping, \
                                       const enum CdefEdgeFlags edges)

cdef_svp64_fn(4, 4);
cdef_svp64_fn(4, 8);
cdef_svp64_fn(8, 8);*/

int cdef_find_dir_svp64(const pixel *img, const ptrdiff_t stride,
                           unsigned *const var HIGHBD_DECL_SUFFIX);

int cdef_find_dir_svp64_real(const pixel *img, const ptrdiff_t stride,
                           unsigned *const var HIGHBD_DECL_SUFFIX);

static ALWAYS_INLINE void cdef_dsp_init_ppc(Dav1dCdefDSPContext *const c) {
    const unsigned flags = dav1d_get_cpu_flags();

    if (!(flags & DAV1D_PPC_CPU_FLAG_SVP64)) return;

#ifdef HAVE_SVP64
    c->dir = cdef_find_dir_svp64;
#endif

}

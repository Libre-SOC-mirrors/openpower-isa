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

#include <Python.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "pypowersim_wrapper_common.h"

#include "common/intops.h"

#include "src/ppc/cdef.h"
#include "src/tables.h"

int cdef_find_dir_svp64(const pixel *img, const ptrdiff_t stride,
                           unsigned *const var HIGHBD_DECL_SUFFIX)
{
    printf("img: %p, stride: %d, var: %p\n", img, stride, var);
    // It cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from input to this pointer, the address was chosen arbitrarily
    uint64_t img_svp64 = 0x100000;
    uint64_t var_svp64 = 0x200000;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements, mandatory: body
    state->binary = PyBytes_FromStringAndSize((const char *)&cdef_find_dir_svp64_real, 100000);

    // Set GPR #3 to the img pointer
    PyObject *img_address = PyLong_FromUnsignedLongLong(img_svp64);
    PyList_SetItem(state->initial_regs, 3, img_address);

    // Set GPR #4 to the output pointer
    PyObject *stride_svp64 = PyLong_FromUnsignedLongLong(stride);
    PyList_SetItem(state->initial_regs, 4, stride_svp64);

    // Load data into PyPowersim buffer from real memory
    for (int i=0; i < 8; i++) {
      for (int j=0; j < 8; j += 4) {
        PyObject *svp64_address = PyLong_FromUnsignedLongLong(img_svp64 + j*2);
        uint64_t val = (uint64_t)(img[j + 0]) & 0xffff;
        val |= ((uint64_t)(img[j + 1]) & 0xffff) << 16;
        val |= ((uint64_t)(img[j + 2]) & 0xffff) << 32;
        val |= ((uint64_t)(img[j + 3]) & 0xffff) << 48;
/*        printf("img: %p -> %04x %04x %04x %04x\t val: %016lx -> %p\n", img + j, (uint16_t)img[j + 0], (uint16_t)img[j + 1], (uint16_t)img[j + 2], (uint16_t)img[j + 3], val, img_svp64 + j*2);

        uint64_t val = (uint64_t)(img[0]) & 0xff;
        val |= ((uint64_t)(img[1]) & 0xff) << 8;
        val |= ((uint64_t)(img[2]) & 0xff) << 16;
        val |= ((uint64_t)(img[3]) & 0xff) << 24;
        val |= ((uint64_t)(img[4]) & 0xff) << 32;
        val |= ((uint64_t)(img[5]) & 0xff) << 40;
        val |= ((uint64_t)(img[6]) & 0xff) << 48;
        val |= ((uint64_t)(img[7]) & 0xff) << 56;
        printf("src: %p -> %02x %02x %02x %02x %02x %02x %02x %02x\t val: %016lx -> %p\n", img, (uint8_t)img[0], (uint8_t)img[1], (uint8_t)img[2], (uint8_t)img[3], (uint8_t)img[4], (uint8_t)img[5], (uint8_t)img[6], (uint8_t)img[7], val, img_svp64);*/
        PyObject *word = PyLong_FromUnsignedLongLong(val);
        PyDict_SetItem(state->initial_mem, svp64_address, word);
      }
      img += stride/2;
      img_svp64 += stride;
    }

    // Set GPR #5 to the var pointer, and clear the address
    PyObject *var_address = PyLong_FromUnsignedLongLong(var_svp64);
    PyList_SetItem(state->initial_regs, 5, var_address);
    {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong(var_svp64);
      PyObject *word = PyLong_FromUnsignedLongLong(0);
      PyDict_SetItem(state->initial_mem, svp64_address, word);
    }

#if BITDEPTH == 16
    const int bitdepth_min_8 = bitdepth_from_max(bitdepth_max) - 8;
    PyObject *bitdepth = PyLong_FromUnsignedLongLong(bitdepth_min_8);
    PyList_SetItem(state->initial_regs, 6, bitdepth);
#endif

    // Prepare the arguments object for the call
    pypowersim_prepareargs(state);

    // Call the function and get the resulting object
    state->result_obj = PyObject_CallObject(state->simulator, state->args);
    if (!state->result_obj) {
        PyErr_Print();
        printf("Error invoking 'run_a_simulation'\n");
        pypowersim_finalize(state);
	exit(1);
    }

    // Get the GPRs from the result_obj
    PyObject *final_regs = PyObject_GetAttrString(state->result_obj, "gpr");
    if (!final_regs) {
        PyErr_Print();
        printf("Error getting final GPRs\n");
        pypowersim_finalize(state);
	exit(1);
    }

    PyObject *memobj = PyObject_GetAttrString(state->result_obj, "mem");
    if (!memobj) {
        PyErr_Print();
        Py_DECREF(state->result_obj);
        printf("Error getting mem object\n");
    }

    PyObject *mem = PyObject_GetAttrString(memobj, "mem");
    if (!mem) {
        PyErr_Print();
        Py_DECREF(state->result_obj);
        printf("Error getting mem dict\n");
    }
    {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong((var_svp64)/8);
      PyObject *pyval = PyDict_GetItem(mem, svp64_address);
      uint64_t val = PyLong_AsUnsignedLongLong(pyval);
      *var = (uint32_t) val;
      printf("output: %p -> %08x\t val: %016lx -> %p\n", var, *var, val, var_svp64);
    }

    // GPR #3 holds the return value as an integer
    PyObject *key = PyLong_FromLongLong(3);
    PyObject *itm = PyDict_GetItem(final_regs, key);
    if (!itm) {
        PyErr_Print();
        printf("Error getting GPR #3\n");
        pypowersim_finalize(state);
	exit(1);
    }
    PyObject *value = PyObject_GetAttrString(itm, "value");
    if (!value) {
        PyErr_Print();
        printf("Error getting value of GPR #3\n");
        pypowersim_finalize(state);
	exit(1);
    }
    uint64_t val = PyLong_AsUnsignedLongLong(value);

    // Return value
    return (uint32_t) val;
}

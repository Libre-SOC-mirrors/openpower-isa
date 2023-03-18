#include <Python.h>
#include <stdint.h>
#include <stdio.h>

#include "pypowersim_wrapper_common.h"
#include "xchacha20_wrapper.h"
#include "xchacha20.h"

void xchacha_hchacha20_svp64(uint8_t *out, const uint8_t *in, const uint8_t *k) {

    // These cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from input to this pointer, the address was chosen arbitrarily
    uint64_t inptr_svp64  = 0x100000;
    uint64_t outptr_svp64 = 0x200000;
    uint64_t keyptr_svp64 = 0x300000;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements, mandatory: body
    state->binary = PyBytes_FromStringAndSize((const char *)&xchacha_hchacha20_svp64_real, 10000);
    // Set GPR #3 to the output pointer
    PyObject *out_address = PyLong_FromUnsignedLongLong(outptr_svp64);
    PyList_SetItem(state->initial_regs, 3, out_address);

    // Set GPR #4 to the input pointer
    PyObject *in_address = PyLong_FromUnsignedLongLong(inptr_svp64);
    PyList_SetItem(state->initial_regs, 4, in_address);

    // Load data into buffer from real memory
    for (int i=0; i < 16; i += 8) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong(inptr_svp64 + i);
      uint64_t *inptr64 = (uint64_t *) in;
      PyObject *word = PyLong_FromUnsignedLongLong(*inptr64);
      PyDict_SetItem(state->initial_mem, svp64_address, word);
      in += 8;
    }

    // Set GPR #5 to the key pointer
    PyObject *key_address = PyLong_FromUnsignedLongLong(keyptr_svp64);
    PyList_SetItem(state->initial_regs, 5, key_address);

    // Load data into buffer from real memory
    for (int i=0; i < 32; i += 8) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong(keyptr_svp64 + i);
      uint64_t *keyptr64 = (uint64_t *) k;
      PyObject *word = PyLong_FromUnsignedLongLong(*keyptr64);
      PyDict_SetItem(state->initial_mem, svp64_address, word);
      k += 8;
    }

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
    uint64_t *outptr64 = (uint64_t *) out;
    for (int i=0; i < 32; i += 8) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong((outptr_svp64 + i)/8);
      PyObject *pyval = PyDict_GetItem(mem, svp64_address);
      uint64_t val = PyLong_AsUnsignedLongLong(pyval);
      *outptr64 = val;
      outptr64++;
    }
}

void xchacha_encrypt_bytes_svp64(XChaCha_ctx *ctx, const uint8_t *m, uint8_t *c, uint32_t bytes) {
    /*uint8_t c2[1000];
    XChaCha_ctx ctx2;
    memcpy(&ctx2, ctx, sizeof(XChaCha_ctx));
    xchacha_encrypt_bytes(&ctx2, m, c2, bytes);*/

    // These cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from input to this pointer, the address was chosen arbitrarily
    uint64_t ctxptr_svp64  = 0x100000;
    uint64_t mptr_svp64 = 0x200000;
    uint64_t cptr_svp64 = 0x300000;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements
    state->binary = PyBytes_FromStringAndSize((const char *)&xchacha_encrypt_bytes_svp64_real, 10000);

    // Set GPR #3 to the output pointer
    PyObject *ctxptr_address = PyLong_FromUnsignedLongLong(ctxptr_svp64);
    PyList_SetItem(state->initial_regs, 3, ctxptr_address);

    // Load data into buffer from real memory
    uint8_t *ctx_u8ptr = (uint8_t *) ctx;
    for (size_t i=0; i < 64; i += 8) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong(ctxptr_svp64);
      uint64_t *ctxptr64 = (uint64_t *) ctx_u8ptr;
      /*printf("ctx[%ld]\t: %p -> %02x %02x %02x %02x %02x %02x %02x %02x\n", i, ctxptr64, ctx_u8ptr[0], ctx_u8ptr[1], ctx_u8ptr[2], ctx_u8ptr[3],
                                                                             ctx_u8ptr[4], ctx_u8ptr[5], ctx_u8ptr[6], ctx_u8ptr[7]);
      printf("val\t: %016lx -> %016lx\n", *ctxptr64, ctxptr_svp64);*/
      PyObject *word = PyLong_FromUnsignedLongLong(*ctxptr64);
      PyDict_SetItem(state->initial_mem, svp64_address, word);
      ctx_u8ptr += 8;
      ctxptr_svp64 += 8;
    }

    // Set GPR #4 to the input pointer
    PyObject *mptr_address = PyLong_FromUnsignedLongLong(mptr_svp64);
    PyList_SetItem(state->initial_regs, 4, mptr_address);

    uint32_t bytes_rem = bytes % 8;
    bytes -= bytes_rem;    
    // Load data into buffer from real memory
    for (size_t i=0; i < bytes; i += 8) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong(mptr_svp64);
      uint64_t *mptr64 = (uint64_t *) m;
      /*printf("m[%ld] \t: %p -> %02x %02x %02x %02x %02x %02x %02x %02x\n", i, mptr64, m[0], m[1], m[2], m[3],
                                                                             m[4], m[5], m[6], m[7]);

      printf("val \t: %016lx -> %016lx\n", *mptr64, mptr_svp64);*/
      PyObject *word = PyLong_FromUnsignedLongLong(*mptr64);
      PyDict_SetItem(state->initial_mem, svp64_address, word);
      m += 8;
      mptr_svp64 += 8;
    }
    // Load remaining bytes
    PyObject *svp64_address = PyLong_FromUnsignedLongLong(mptr_svp64);
    uint64_t mptr64 = 0;
    uint8_t *mptr8 = (uint8_t *) &mptr64;
    for (size_t i=0; i < bytes_rem; i++) {
        mptr8[i] = m[i];
    }
    PyObject *word = PyLong_FromUnsignedLongLong(mptr64);
    PyDict_SetItem(state->initial_mem, svp64_address, word);

    // Set GPR #5 to the cipher pointer
    PyObject *cptr_address = PyLong_FromUnsignedLongLong(cptr_svp64);
    PyList_SetItem(state->initial_regs, 5, cptr_address);

    // Set GPR #r65 to the cipher pointer
    PyObject *bytes_svp64 = PyLong_FromUnsignedLongLong(bytes);
    PyList_SetItem(state->initial_regs, 6, bytes_svp64);

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

    uint64_t *cptr64 = (uint64_t *) c;
    for (size_t i=0; i < (bytes/8+1)*8; i += 8) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong((cptr_svp64 + i)/8);
      PyObject *pyval = PyDict_GetItem(mem, svp64_address);
      uint64_t val = PyLong_AsUnsignedLongLong(pyval);
      *cptr64 = val;
      //printf("c: %p -> %016lx\t val: %016lx -> %lx\n", cptr64, *cptr64, val, cptr_svp64 + i);
      cptr64++;
    }
/*
    for (size_t i=0; i < (bytes/8+1)*8; i+= 8) {
      printf("c[%ld]  : %02x %02x %02x %02x %02x %02x %02x %02x\n", i, c[i+0], c[i+1], c[i+2], c[i+3],
                                                                        c[i+4], c[i+5], c[i+6], c[i+7]);
      printf("c2[%ld] : %02x %02x %02x %02x %02x %02x %02x %02x\n", i, c2[i+0], c2[i+1], c2[i+2], c2[i+3],
                                                                        c2[i+4], c2[i+5], c2[i+6], c2[i+7]);
    }*/

}

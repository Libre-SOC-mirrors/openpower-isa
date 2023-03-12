#include <Python.h>
#include <stdint.h>
#include <stdio.h>

#include "pypowersim_wrapper_common.h"
#include "xchacha20_wrapper.h"
#include "xchacha20.h"

void xchacha_hchacha20_svp64(uint8_t *out, const uint8_t *in, const uint8_t *k) {

    uint8_t out2[32];
    xchacha_hchacha20(out2, in, k);

    // These cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from input to this pointer, the address was chosen arbitrarily
    uint64_t inptr_svp64  = 0x100000;
    uint64_t outptr_svp64 = 0x200000;
    uint64_t keyptr_svp64 = 0x300000;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements, mandatory: body
    state->binary = PyBytes_FromStringAndSize((const char *)&xchacha_hchacha20_svp64_real, 1000);
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
/*      printf("in[%d] \t: %p -> %02x %02x %02x %02x %02x %02x %02x %02x\n", i, inptr64, in[i+0], in[i+1], in[i+2], in[i+3],
                                                                             in[i+4], in[i+5], in[i+6], in[i+7]);

      printf("val \t: %016lx -> %016lx\n", *inptr64, inptr_svp64 + i);*/
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
/*      printf("k[%d] \t: %p -> %02x %02x %02x %02x %02x %02x %02x %02x\n", i, keyptr64, k[i+0], k[i+1], k[i+2], k[i+3],
                                                                             k[i+4], k[i+5], k[i+6], k[i+7]);

      printf("val \t: %016lx -> %016lx\n", *keyptr64, keyptr_svp64 + i);*/
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
      printf("out: %p -> %016lx\t val: %016lx -> %lx\n", outptr64, *outptr64, val, outptr_svp64 + i);
      outptr64++;
    }

    for (int i=0; i < 32; i+= 8) {
      printf("out[%d]  : %02x %02x %02x %02x %02x %02x %02x %02x\n", i, out[i+0], out[i+1], out[i+2], out[i+3],
                                                                        out[i+4], out[i+5], out[i+6], out[i+7]);
      printf("out2[%d] : %02x %02x %02x %02x %02x %02x %02x %02x\n", i, out2[i+0], out2[i+1], out2[i+2], out2[i+3],
                                                                        out2[i+4], out2[i+5], out2[i+6], out2[i+7]);

    }
}

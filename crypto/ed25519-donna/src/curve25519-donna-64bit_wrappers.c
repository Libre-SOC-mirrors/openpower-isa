#include <Python.h>
#include <stdint.h>
#include <stdio.h>

#include "pypowersim_wrapper_common.h"
#include "curve25519-donna-64bit_wrappers.h"

const char *curve25519_donna_64bit_svp64_filename = "./bin/curve25519-donna-64bit_svp64.bin";

void
curve25519_copy_svp64(bignum25519 out, const bignum25519 in) {

    // These cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from input to this pointer, the address was chosen arbitrarily
    uint64_t outptr_svp64  = 0x100000;
    uint64_t inptr_svp64 = 0x200000;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements
    state->binary = PyBytes_FromStringAndSize(curve25519_donna_64bit_svp64_filename, strlen(curve25519_donna_64bit_svp64_filename));

    // Set GPR #3 to the out bignum25519 pointer
    PyObject *outptr_address = PyLong_FromUnsignedLongLong(outptr_svp64);
    PyList_SetItem(state->initial_regs, 2, outptr_address);

    // Set GPR #4 to the input pointer
    PyObject *inptr_address = PyLong_FromUnsignedLongLong(inptr_svp64);
    PyList_SetItem(state->initial_regs, 3, inptr_address);

    // Load data into buffer from real memory
    for (size_t i = 0; i < sizeof(bignum25519)/sizeof(uint64_t); i++) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong(inptr_svp64 + i*8);
      uint64_t inptr64 = in[i];
      printf("val \t: %016lx -> %016lx\n", inptr64, inptr_svp64);
      PyObject *word = PyLong_FromUnsignedLongLong(inptr64);
      PyDict_SetItem(state->initial_mem, svp64_address, word);
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

    for (size_t i = 0; i < sizeof(bignum25519)/sizeof(uint64_t); i++) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong((outptr_svp64 + i*8)/8);
      PyObject *pyval = PyDict_GetItem(mem, svp64_address);
      uint64_t val = PyLong_AsUnsignedLongLong(pyval);
      out[i] = val;
      printf("out[%ld]: %016lx\t val: %016lx -> %lx\n", i, out[i], val, outptr_svp64 + i*8);
    }
}

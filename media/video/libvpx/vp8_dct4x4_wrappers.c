#include <Python.h>
#include <stdint.h>
#include <stdio.h>

#include "pypowersim_wrapper_common.h"
#include "vp8_dct4x4_wrappers.h"
#include "vp8_rtcd.h"

void vp8_short_fdct4x4_svp64(int16_t *input, int16_t *output, int32_t pitch) {

    printf("pitch: %d\n", pitch);
    int16_t output2[16];
    vp8_short_fdct4x4_c(input, output2, pitch);


    // It cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from input to this pointer, the address was chosen arbitrarily
    uint64_t input_svp64  = 0x100000;
    uint64_t output_svp64 = 0x200000;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements, mandatory: body
    state->binary = PyBytes_FromStringAndSize((const char *)&vp8_short_fdct4x4_svp64_real, 1000);
    // Set GPR #3 to the input pointer
    PyObject *address = PyLong_FromUnsignedLongLong(input_svp64);
    PyList_SetItem(state->initial_regs, 3, address);
    // Load data into buffer from real memory
    for (int i=0; i < 16; i += 4) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong(input_svp64 + i*2);
      uint64_t val = (uint64_t)(input[0]) & 0xffff;
      val |= ((uint64_t)(input[1]) & 0xffff) << 16;
      val |= ((uint64_t)(input[2]) & 0xffff) << 32;
      val |= ((uint64_t)(input[3]) & 0xffff) << 48;
      //printf("src: %p -> %04x %04x %04x %04x\t val: %016lx -> %p\n", input, (uint16_t)input[0], (uint16_t)input[1], (uint16_t)input[2], (uint16_t)input[3], val, input_svp64);
      PyObject *word = PyLong_FromUnsignedLongLong(val);
      PyDict_SetItem(state->initial_mem, svp64_address, word);
      input += 4;
    }
    // Set GPR #4 to the output pointer
    PyObject *out_address = PyLong_FromUnsignedLongLong(output_svp64);
    PyList_SetItem(state->initial_regs, 4, out_address);

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
    for (int i=0; i < 16; i += 4) {
      PyObject *svp64_address = PyLong_FromUnsignedLongLong((output_svp64 + i*2)/8);
      PyObject *pyval = PyDict_GetItem(mem, svp64_address);
      uint64_t val = PyLong_AsUnsignedLongLong(pyval);
      output[i + 0] = (uint16_t) val;
      output[i + 1] = (uint16_t) (val >> 16);
      output[i + 2] = (uint16_t) (val >> 32);
      output[i + 3] = (uint16_t) (val >> 48);
      //printf("output: %p -> %04x %04x %04x %04x\t val: %016lx -> %p\n", output, (uint16_t)output[i], (uint16_t)output[i + 1], (uint16_t)output[i + 2], (uint16_t)output[i + 3], val, output_svp64);
    }

    /*for (int i=0; i < 16; i += 4) {
      printf("output[%d] : %04x %04x %04x %04x\n", i, (uint16_t)output[i],  (uint16_t)output[i+1],  (uint16_t)output[i+2],  (uint16_t)output[i+3]);
      printf("output2[%d]: %04x %04x %04x %04x\n", i, (uint16_t)output2[i], (uint16_t)output2[i+1], (uint16_t)output2[i+2], (uint16_t)output2[i+3]);
    }*/
}

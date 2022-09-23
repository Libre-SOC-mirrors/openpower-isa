#include <Python.h>
#include <stdint.h>
#include <stdio.h>

#include "pypowersim_wrapper_common.h"
#include "variance_svp64_wrappers.h"
#include "variance_ref.h"

uint32_t vpx_get_mb_ss_svp64(const int16_t *src_ptr) {
    // It cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from src_ptr to this pointer, the address was chosen arbitrarily
    uint64_t src_ptr_svp64 = 0x100000;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements, mandatory: body
    //
    state->binary = PyBytes_FromStringAndSize((const char *)&vpx_get_mb_ss_svp64_real, 1000);
    // Set GPR #3 to the pointer
    PyObject *address = PyLong_FromLongLong(src_ptr_svp64);
    PyList_SetItem(state->initial_regs, 3, address);
    // Load data into buffer from real memory
    for (int i=0; i < 256; i += 4) {
      PyObject *address = PyLong_FromLongLong(src_ptr_svp64);
      uint64_t val = src_ptr[0];
      val |= (uint64_t)(src_ptr[1]) << 16;
      val |= (uint64_t)(src_ptr[2]) << 32;
      val |= (uint64_t)(src_ptr[3]) << 48;
      //printf("src: %p -> %04x %04x %04x %04x, val: %016x -> %p\n", src_ptr, src_ptr[0], src_ptr[1], src_ptr[2], src_ptr[3], val, src_ptr_svp64);
      PyObject *word = PyLong_FromLongLong(val);
      PyDict_SetItem(state->initial_mem, address, word);
      src_ptr += 4;
      src_ptr_svp64 += 8;
    }

    // Prepare the arguments object for the call
    pypowersim_prepareargs(state);

    // Call the function and get the resulting object
    state->result_obj = PyObject_CallObject(state->simulator, state->args);
    Py_DECREF(state->simulator);
    Py_DECREF(state->args);
    if (!state->result_obj) {
        PyErr_Print();
        printf("Error invoking 'run_a_simulation'\n");
    }

    // Get the GPRs from the result_obj
    PyObject *final_regs = PyObject_GetAttrString(state->result_obj, "gpr");
    if (!final_regs) {
        PyErr_Print();
        Py_DECREF(state->result_obj);
        printf("Error getting final GPRs\n");
    }

    // GPR #3 holds the return value as an integer
    PyObject *key = PyLong_FromLongLong(3);
    PyObject *itm = PyDict_GetItem(final_regs, key);
    PyObject *value = PyObject_GetAttrString(itm, "value");
    uint64_t val = PyLong_AsLongLong(value);

    // Return value
    return (uint32_t) val;
}

uint32_t vpx_get4x4sse_cs_svp64(const uint8_t *src_ptr, int src_stride,
                                const uint8_t *ref_ptr, int ref_stride) {

    // It cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from src_ptr to this pointer, the address was chosen arbitrarily
    uint64_t src_ptr_svp64 = 0x100000;
    uint64_t ref_ptr_svp64 = 0x200000;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements, mandatory: body
    state->binary = PyBytes_FromStringAndSize((const char *)&vpx_get4x4sse_cs_svp64_real, 1000);
    // Set GPR #3 to the src_ptr
    PyObject *src_address = PyLong_FromLongLong(src_ptr_svp64);
    PyList_SetItem(state->initial_regs, 3, src_address);
    // Load data into buffer from real memory
    for (int r=0; r < 4; r++) {
      PyObject *address = PyLong_FromLongLong(src_ptr_svp64);
      uint64_t val = src_ptr[0];
      val |= (uint64_t)(src_ptr[1]) << 16;
      val |= (uint64_t)(src_ptr[2]) << 32;
      val |= (uint64_t)(src_ptr[3]) << 48;
      PyObject *word = PyLong_FromLongLong(val);
      PyDict_SetItem(state->initial_mem, address, word);
      src_ptr += src_stride;
      src_ptr_svp64 += 8;
    }

    // Set GPR #4 to the src_stride 
    PyList_SetItem(state->initial_regs, 4, PyLong_FromLongLong(src_stride));

    // Set GPR #5 to the ref_ptr
    PyObject *ref_address = PyLong_FromLongLong(ref_ptr_svp64);
    PyList_SetItem(state->initial_regs, 5, ref_address);
    // Load data into buffer from real memory
    for (int r=0; r < 4; r++) {
      PyObject *address = PyLong_FromLongLong(ref_ptr_svp64);
      uint64_t val = ref_ptr[0];
      val |= (uint64_t)(ref_ptr[1]) << 16;
      val |= (uint64_t)(ref_ptr[2]) << 32;
      val |= (uint64_t)(ref_ptr[3]) << 48;
      //printf("ref: %p -> %04x %04x %04x %04x, val: %016lx -> %p\n", ref_ptr, ref_ptr[0], ref_ptr[1], ref_ptr[2], ref_ptr[3], val, ref_ptr_svp64);
      PyObject *word = PyLong_FromLongLong(val);
      PyDict_SetItem(state->initial_mem, address, word);
      ref_ptr += ref_stride;
      ref_ptr_svp64 += 8;
    }

    // Set GPR #6 to the ref_stride 
    PyList_SetItem(state->initial_regs, 6, PyLong_FromLongLong(ref_stride));

    // Prepare the arguments object for the call
    pypowersim_prepareargs(state);

    // Call the function and get the resulting object
    state->result_obj = PyObject_CallObject(state->simulator, state->args);
    Py_DECREF(state->simulator);
    Py_DECREF(state->args);
    if (!state->result_obj) {
        PyErr_Print();
        printf("Error invoking 'run_a_simulation'\n");
    }

    // Get the GPRs from the result_obj
    PyObject *final_regs = PyObject_GetAttrString(state->result_obj, "gpr");
    if (!final_regs) {
        PyErr_Print();
        Py_DECREF(state->result_obj);
        printf("Error getting final GPRs\n");
    }

    // GPR #3 holds the return value as an integer
    PyObject *key = PyLong_FromLongLong(3);
    PyObject *itm = PyDict_GetItem(final_regs, key);
    PyObject *value = PyObject_GetAttrString(itm, "value");
    uint64_t val = PyLong_AsLongLong(value);

    // Return value
    return (uint32_t) val;
}

void variance_svp64(const uint8_t *src_ptr, int src_stride,
                    const uint8_t *ref_ptr, int ref_stride, int w, int h,
                    uint32_t *sse, int *sum) {

    int sse2, sum2;
    variance_c(src_ptr, src_stride, ref_ptr, ref_stride, w, h, &sse2, &sum2);
    printf("src_ptr: %p, src_stride: %d, ref_ptr: %p, ref_stride: %d, w: %d, h: %d, sse_ptr: %p, sum_ptr: %p, sse2: %d, sum2: %d\n",
		    src_ptr, src_stride, ref_ptr, ref_stride, w, h, sse, sum, sse2, sum2);
    // It cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from src_ptr to this pointer, the address was chosen arbitrarily
    uint64_t src_ptr_svp64 = 0x100000;
    uint64_t ref_ptr_svp64 = 0x200000;
    uint64_t sse_ptr_svp64 = 0x300000;
    uint64_t sum_ptr_svp64 = 0x300008;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements, mandatory: body
    state->binary = PyBytes_FromStringAndSize((const char *)&variance_svp64_real, 1000);
    // Set GPR #3 to the src_ptr
    PyObject *src_address = PyLong_FromLongLong(src_ptr_svp64);
    PyList_SetItem(state->initial_regs, 3, src_address);
    // Load data into buffer from real memory
    for (int r=0; r < 4; r++) {
      PyObject *address = PyLong_FromLongLong(src_ptr_svp64);
      uint64_t val = src_ptr[0];
      val |= (uint64_t)(src_ptr[1]) << 16;
      val |= (uint64_t)(src_ptr[2]) << 32;
      val |= (uint64_t)(src_ptr[3]) << 48;
      PyObject *word = PyLong_FromLongLong(val);
      PyDict_SetItem(state->initial_mem, address, word);
      src_ptr += src_stride;
      src_ptr_svp64 += 8;
    }

    // Set GPR #4 to the src_stride 
    PyList_SetItem(state->initial_regs, 4, PyLong_FromLongLong(src_stride));

    // Set GPR #5 to the ref_ptr
    PyObject *ref_address = PyLong_FromLongLong(ref_ptr_svp64);
    PyList_SetItem(state->initial_regs, 5, ref_address);
    // Load data into buffer from real memory
    for (int r=0; r < 4; r++) {
      PyObject *address = PyLong_FromLongLong(ref_ptr_svp64);
      uint64_t val = ref_ptr[0];
      val |= (uint64_t)(ref_ptr[1]) << 16;
      val |= (uint64_t)(ref_ptr[2]) << 32;
      val |= (uint64_t)(ref_ptr[3]) << 48;
      //printf("ref: %p -> %04x %04x %04x %04x, val: %016lx -> %p\n", ref_ptr, ref_ptr[0], ref_ptr[1], ref_ptr[2], ref_ptr[3], val, ref_ptr_svp64);
      PyObject *word = PyLong_FromLongLong(val);
      PyDict_SetItem(state->initial_mem, address, word);
      ref_ptr += ref_stride;
      ref_ptr_svp64 += 8;
    }

    // Set GPR #6 to the ref_stride 
    PyList_SetItem(state->initial_regs, 6, PyLong_FromLongLong(ref_stride));
    // Set GPR #7 to the width
    PyList_SetItem(state->initial_regs, 7, PyLong_FromLongLong(w));
    // Set GPR #8 to the height
    PyList_SetItem(state->initial_regs, 8, PyLong_FromLongLong(h));
    // Set GPR #9 to the sse pointer
    PyList_SetItem(state->initial_regs, 9, PyLong_FromLongLong(sse_ptr_svp64));
    // Set GPR #10 to the sum pointer
    PyList_SetItem(state->initial_regs, 10, PyLong_FromLongLong(sum_ptr_svp64));

    PyObject *sse_address = PyLong_FromLongLong(sse_ptr_svp64);
    PyObject *sum_address = PyLong_FromLongLong(sum_ptr_svp64);
    PyObject *word = PyLong_FromLongLong(0);
    PyDict_SetItem(state->initial_mem, sse_address, word);
    PyDict_SetItem(state->initial_mem, sum_address, word);

    // Prepare the arguments object for the call
    pypowersim_prepareargs(state);

    // Call the function and get the resulting object
    state->result_obj = PyObject_CallObject(state->simulator, state->args);
    Py_DECREF(state->simulator);
    Py_DECREF(state->args);
    if (!state->result_obj) {
        PyErr_Print();
        printf("Error invoking 'run_a_simulation'\n");
    }

    // Get the GPRs from the result_obj
    PyObject *final_regs = PyObject_GetAttrString(state->result_obj, "gpr");
    if (!final_regs) {
        PyErr_Print();
        Py_DECREF(state->result_obj);
        printf("Error getting final GPRs\n");
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

    sse_address = PyLong_FromLongLong(sse_ptr_svp64/8);
    sum_address = PyLong_FromLongLong(sum_ptr_svp64/8);

    PyObject *sse_val = PyDict_GetItem(mem, sse_address);
    *sse = (uint32_t) PyLong_AsLongLong(sse_val);

    PyObject *sum_val = PyDict_GetItem(mem, sum_address);
    *sum = (int32_t)PyLong_AsLongLong(sum_val);
    printf("sse: %d/%08x, sum: %d/%08x\n", *sse, *sse, *sum, *sum);
}

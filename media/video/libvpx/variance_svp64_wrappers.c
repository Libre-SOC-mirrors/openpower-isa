#include <Python.h>
#include <stdint.h>
#include <stdio.h>

#include "pypowersim_wrapper_common.h"
#include "variance_svp64_wrappers.h"

uint32_t vpx_get_mb_ss_svp64(const int16_t *src_ptr) {
    // It cannot be the same pointer as the original function, as it is really a separate CPU/RAM
    // we have to memcpy from src_ptr to this pointer, the address was chosen arbitrarily
    const uint64_t src_ptr_svp64 = 0x100000;
    const uint64_t *src_ptr64 = (const uint64_t *) src_ptr;

    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements, mandatory: body
    //
    state->binary = PyBytes_FromStringAndSize((const char *)&vpx_get_mb_ss_svp64_real, 1000);
    // Set GPR #3 to the pointer
    PyObject *address = PyLong_FromLongLong(src_ptr_svp64);
    PyList_SetItem(state->initial_regs, 3, address);
    // Load data into buffer from real memory
    size_t size = 256*sizeof(uint16_t)/sizeof(uint64_t);
    for (int i=0; i < size; i++) {
      PyObject *address = PyLong_FromLongLong(src_ptr_svp64 + i*8);
      PyObject *word = PyLong_FromLongLong(*(src_ptr64 + i));
      PyDict_SetItem(state->initial_mem, address, word);
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
    PyObject *key = PyLong_FromLong(3);
    PyObject *itm = PyDict_GetItem(final_regs, key);
    PyObject *value = PyObject_GetAttrString(itm, "value");
    uint64_t val = PyLong_AsLongLong(value);

    // Return value
    return (uint32_t) val;
}

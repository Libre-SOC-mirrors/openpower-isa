#include <Python.h>
#include <stdint.h>
#include <stdio.h>

#include "pypowersim_wrapper_common.h"

int test_function(int x) {
    int result = 0;
    for (int i=0; i < x; i++)
        result += 2*i;
    return result;
}

int test_function_wrapper(int x) {
    // Create the pypowersim_state
    pypowersim_state_t *state = pypowersim_prepare();

    // Change the relevant elements, mandatory: body
    //
    state->binary = PyBytes_FromStringAndSize((const char *)&test_function, 1000);
    // Set GPR #3 to the argument x
    PyList_SetItem(state->initial_regs, 3, PyLong_FromLong(x));

    // Prepare the args object
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

    Py_DECREF(state->result_obj);

    pypowersim_finalize(state);

    // Return value
    return val;
}

int main(int argc, char* argv[]) {
    for (int i=0; i < 20; i++) {
       int result = test_function_wrapper(i);
       printf("i = %d, result = %d\n", i, result);
    }
    return 0;
}



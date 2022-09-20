#include <Python.h>
#include <stdint.h>
#include <stdio.h>

static const char* PLUGIN_NAME = "pypowersim";

typedef struct pypowersim_state {
    PyObject *name;
    PyObject *plugin_module;
    PyObject *binary;
    PyObject *bigendian;
    PyObject *prog;
    PyObject *qemu_cosim;
    PyObject *initial_regs;
    PyObject *initial_sprs;
    PyObject *svstate;
    PyObject *mmu;
    PyObject *initial_cr;
    PyObject *initial_mem;
    PyObject *initial_fprs;
    PyObject *initial_pc;
    PyObject *args;
    PyObject *simulator;
    PyObject *result_obj;
} pypowersim_state_t;

pypowersim_state_t *pypowersim_prepare(void) {
    // Initialize Python C API
    Py_Initialize();
    // Add pypowersim directory to Python path
    PyObject* sysPath = PySys_GetObject((char*)"path");
    PyObject* curDir = PyUnicode_FromString("../../../src/openpower/decoder/isa/");
    PyList_Append(sysPath, curDir);
    Py_DECREF(curDir);

    // Allocate memory for state
    pypowersim_state_t *state = malloc(sizeof(pypowersim_state_t));
    if (!state) {
        printf("Error creating pypowersim_state object\n");
	exit(1);
    }
    // Set plugin name and module
    state->name = PyUnicode_FromString(PLUGIN_NAME);
    state->plugin_module = PyImport_Import(state->name);
    Py_DECREF(state->name);
    if (!state->plugin_module) {
        PyErr_Print();
        printf("Error importing module\n");
	exit(1);
    }
    // Set simulator object
    state->simulator = PyObject_GetAttrString(state->plugin_module, "run_a_simulation");
    Py_DECREF(state->plugin_module);
    if (!state->simulator) {
        PyErr_Print();
        printf("Error retrieving 'run_a_simulation'\n");
	exit(1);
    }

    // Little Endian for now
    state->bigendian = Py_False;
    state->prog = Py_None;
    state->qemu_cosim = Py_False;
    // Set and clear 128 GPRs
    state->initial_regs = PyList_New(128);
    for (int i=0; i < 128; i++) {
       PyList_SetItem(state->initial_regs, i, PyLong_FromLong(0));
    }
    // Create SPRs to all bits set
    state->initial_sprs= PyDict_New();
    PyDict_SetItemString(state->initial_sprs, "LR",  PyLong_FromLong(0xffffff));
    // Set empty SVSTATE
    state->svstate = PyLong_FromLong(0);
    // Set no MMU
    state->mmu = Py_None;
    // Set no initial CR
    state->initial_cr = PyLong_FromLong(0);
    // Set empty initial Memory
    state->initial_mem = PyDict_New();
    // Set and Clear 128 FPR
    state->initial_fprs = PyList_New(128);
    for (int i=0; i < 128; i++) {
       PyList_SetItem(state->initial_fprs, i, PyLong_FromLong(0));
    }
    // Set initial Program Counter
    state->initial_pc= PyLong_FromLong(0x0);

    return state;
}

void pypowersim_prepareargs(pypowersim_state_t *state) {
    // Set the tuple with the state objects
    state->args = PyTuple_Pack(12, state->binary, state->bigendian, state->prog, state->qemu_cosim,
		                  state->initial_regs, state->initial_sprs, state->svstate, state->mmu,
				  state->initial_cr, state->initial_mem, state->initial_fprs, state->initial_pc );
    if (!state->args) {
        PyErr_Print();
        Py_DECREF(state->simulator);
        printf("Error building args tuple\n");
	exit(1);
    }
}

void pypowersim_finalize(void) {
    // Finalize Python C API
    Py_Finalize();
}


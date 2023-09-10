#include <Python.h>
#include <stdint.h>
#include <stdio.h>
#include <pwd.h>
#include <string.h>

static const char* PLUGIN_NAME = "pypowersim";
static int python_initialized = 0;
static PyObject *plugin_name = NULL;
static PyObject *plugin_module = NULL;

typedef struct pypowersim_state {
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

static pypowersim_state_t *pypowersim_prepare(void) {
    // Allocate memory for state
    pypowersim_state_t *state = malloc(sizeof(pypowersim_state_t));
    if (!state) {
        printf("Error creating pypowersim_state object\n");
	exit(1);
    }
    memset(state, 0, sizeof(pypowersim_state_t));

    // Add pypowersim directory to Python path
    if (!python_initialized) {
      // Initialize Python C API
      Py_Initialize();

      // To construct directory based on username, need $HOME
      char homeIsaDir[100];
      const char *homeDir = getenv("HOME"); // user specific - /home/[USER NAME]
      strcat(homeIsaDir, homeDir);
      strcat(homeIsaDir, "/src/openpower-isa/src/openpower/decoder/isa/");
      printf(homeIsaDir);

      PyObject* sysPath = PySys_GetObject((char*)"path");
      PyObject* curDir = PyUnicode_FromString(homeIsaDir);
      PyList_Append(sysPath, curDir);
      Py_DECREF(curDir);

      // Set plugin name and module
      plugin_name = PyUnicode_FromString(PLUGIN_NAME);
      plugin_module = PyImport_Import(plugin_name);
      Py_DECREF(plugin_name);
      if (!plugin_module) {
          PyErr_Print();
          printf("Error importing module\n");
    	exit(1);
      }
      python_initialized = 1;
    }

    // Set simulator object
    state->simulator = PyObject_GetAttrString(plugin_module, "run_a_simulation");
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

static void pypowersim_prepareargs(pypowersim_state_t *state) {
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

static void pypowersim_finalize(pypowersim_state_t *state) {
    if (state->simulator) Py_DECREF(state->simulator);
    if (state->binary) Py_DECREF(state->binary);
    if (state->bigendian) Py_DECREF(state->bigendian);
    if (state->prog) Py_DECREF(state->prog);
    if (state->qemu_cosim) Py_DECREF(state->qemu_cosim);
    if (state->initial_regs) Py_DECREF(state->initial_regs);
    if (state->initial_sprs) Py_DECREF(state->initial_sprs);
    if (state->svstate) Py_DECREF(state->svstate);
    if (state->mmu) Py_DECREF(state->mmu);
    if (state->initial_cr) Py_DECREF(state->initial_cr);
    if (state->initial_mem) Py_DECREF(state->initial_mem);
    if (state->initial_fprs) Py_DECREF(state->initial_fprs);
    if (state->initial_pc) Py_DECREF(state->initial_pc);
    if (state->args) Py_DECREF(state->args);
    if (state->result_obj) Py_DECREF(state->result_obj);
    memset(state, 0, sizeof(pypowersim_state_t));
    if (state) free(state);

    // Finalize Python C API
    // Py_Finalize();
}


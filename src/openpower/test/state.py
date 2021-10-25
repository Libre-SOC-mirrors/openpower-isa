""" Power ISA test API

This module implements the creation, inspection and comparison
of test states from different sources.

The basic premise is to create a test state using the TestState method.
The TestState method returns a test state object initialized with a
basic set of registers pulled from the 'to_test' object.  The
state created can then be tested against other test states using the
'compare' method.

The SimState class provides an example of needed registers and naming.

The TestState method relies on the 'state_factory' dictionary for lookup
of associated test class creation.  The dictionary can be added to using
the state_add method.

Also note when creating and accessing test state classes and object
methods, the use of yield from/yield is required.


"""


from openpower.decoder.power_enums import XER_bits
from openpower.util import log

global staterunner_factory
staterunner_factory = {}


def staterunner_add(name, kls):
    log("staterunner_add", name, kls)
    staterunner_factory[name] = kls


# TBD an Abstract Base Class
class StateRunner:
    """StateRunner: an Abstract Base Class for preparing and running "State".
    near-identical in concept to python unittest.TestCase
    """
    def __init__(self, name, kls):
        staterunner_add(name, kls)
        self.name = name

    def setup_for_test(self):
        if False: yield
    def setup_during_test(self):
        if False: yield
    def prepare_for_test(self, test):
        if False: yield
    def run_test(self):
        if False: yield
    def end_test(self):
        if False: yield
    def cleanup(self):
        if False: yield


class State:
    """State: Base class for the "state" of the Power ISA object to be tested
    including methods to compare various registers and memory between
    them.

    All methods implemented must be generators.

    GPRs and CRs - stored as lists
    XERs/PC - simple members
    memory - stored as a dictionary {location: data}
    """
    def get_state(self):
        yield from self.get_intregs()
        yield from self.get_crregs()
        yield from self.get_xregs()
        yield from self.get_pc()
        yield from self.get_mem()

    def compare(self, s2):
        # Compare int registers
        for i, (self.intregs, s2.intregs) in enumerate(
                zip(self.intregs, s2.intregs)):
            log("asserting...reg", i, self.intregs, s2.intregs)
            log("code, frepr(code)", self.code, repr(self.code))
            self.dut.assertEqual(self.intregs, s2.intregs,
                "int reg %d (%s) not equal (%s) %s. got %x  expected %x" %
                (i, self.state_type, s2.state_type, repr(self.code),
                self.intregs, s2.intregs))

        # CR registers
        for i, (self.crregs, s2.crregs) in enumerate(
                zip(self.crregs, s2.crregs)):
            log("asserting...cr", i, self.crregs, s2.crregs)
            self.dut.assertEqual(self.crregs, s2.crregs,
                "cr reg %d (%s) not equal (%s) %s. got %x  expected %x" %
                (i, self.state_type, s2.state_type, repr(self.code),
                self.crregs, s2.crregs))

        # XER
        self.dut.assertEqual(self.so, s2.so, "so mismatch (%s != %s) %s" %
            (self.state_type, s2.state_type, repr(self.code)))
        self.dut.assertEqual(self.ov, s2.ov, "ov mismatch (%s != %s) %s" %
            (self.state_type, s2.state_type, repr(self.code)))
        self.dut.assertEqual(self.ca, s2.ca, "ca mismatch (%s != %s) %s" %
            (self.state_type, s2.state_type, repr(self.code)))

        # pc
        self.dut.assertEqual(self.pc, s2.pc, "pc mismatch (%s != %s) %s" %
            (self.state_type, s2.state_type, repr(self.code)))

    def compare_mem(self, s2):
        # copy dics to preserve state mem then pad empty locs since
        # different Power ISA objects may differ how theystore memory
        s1mem, s2mem = self.mem.copy(), s2.mem.copy()
        for i in set(self.mem).difference(set(s2.mem)):
            s2mem[i] = 0
        for i in set(s2.mem).difference(set(self.mem)):
            s1mem[i] = 0
        for i in s1mem:
            self.dut.assertEqual(s1mem[i], s2mem[i],
                "mem mismatch location %d %s" % (i, self.code))


class SimState(State):
    """SimState: Obtains registers and memory from an ISACaller object.
    Note that yields are "faked" to maintain consistency and compatability
    within the API.
    """
    def __init__(self, sim):
        self.sim = sim

    def get_intregs(self):
        if False:
            yield
        self.intregs = []
        for i in range(32):
            simregval = self.sim.gpr[i].asint()
            self.intregs.append(simregval)
        log("class sim int regs", list(map(hex, self.intregs)))

    def get_crregs(self):
        if False:
            yield
        self.crregs = []
        for i in range(8):
            cri = self.sim.crl[7 - i].get_range().value
            self.crregs.append(cri)
        log("class sim cr regs", list(map(hex, self.crregs)))

    def get_xregs(self):
        if False:
            yield
        self.xregs = []
        self.so = self.sim.spr['XER'][XER_bits['SO']].value
        self.ov = self.sim.spr['XER'][XER_bits['OV']].value
        self.ov32 = self.sim.spr['XER'][XER_bits['OV32']].value
        self.ca = self.sim.spr['XER'][XER_bits['CA']].value
        self.ca32 = self.sim.spr['XER'][XER_bits['CA32']].value
        self.ov = self.ov | (self.ov32 << 1)
        self.ca = self.ca | (self.ca32 << 1)
        self.xregs.extend((self.so, self.ov, self.ca))
        log("class sim xregs", list(map(hex, self.xregs)))

    def get_pc(self):
        if False:
            yield
        self.pcl = []
        self.pc = self.sim.pc.CIA.value
        self.pcl.append(self.pc)
        log("class sim pc", hex(self.pc))

    def get_mem(self):
        if False:
            yield
        keys = list(self.sim.mem.mem.keys())
        self.mem = {}
        # from each address in the underlying mem-simulated dictionary
        # issue a 64-bit LD (with no byte-swapping)
        for k in keys:
            data = self.sim.mem.ld(k*8, 8, False)
            self.mem[k*8] = data


class ExpectedState(State):
    """ExpectedState: A user defined state set manually.
    No methods, just pass into what expected values you want to test
    with against other states.

    see openpower/test/shift_rot/shift_rot_cases2.py for examples
    """
    def __init__(self, int_regs=None, pc=0, crregs=None,
                 so=0, ov=0, ca=0):
        if int_regs is None:
            int_regs = 32
        if isinstance(int_regs, int):
            int_regs = [0] * int_regs
        self.intregs = int_regs
        self.pc = pc
        if crregs is None:
            crregs = 8
        if isinstance(crregs, int):
            crregs = [0] * crregs
        self.crregs = crregs
        self.so = so
        self.ov = ov
        self.ca = ca

    def get_intregs(self):
        if False: yield
    def get_crregs(self):
        if False: yield
    def get_xregs(self):
        if False: yield
    def get_pc(self):
        if False: yield
    def get_mem(self):
        if False: yield

    def dump_state_tofile(self, state, testname):
        """dump_state_tofile:  Takes a passed in teststate object along
        with a test name and generates a code file located at /tmp/testname
        to set an expected state object
        """
        lindent = ' '*8 # indent for code
        with open("/tmp/{0}.py".format(testname), "w") as sout:
            # pc and intregs
            sout.write(f"{lindent}e = ExpectedState(pc={state.pc})\n")
            for i in range(32):
                if(state.intregs[i] != 0):
                    sout.write("{0}e.intregs[{1}] = 0x{2:x}\n".format(
                               lindent,
                               i,
                               state.intregs[i]))
            # cr
            for i in range(8):
                if(state.crregs[i] != 0):
                    sout.write("{0}e.crregs[{1}] = 0x{2:x}\n".format(
                               lindent,
                               i,
                               state.crregs[i]))
            # XER
            if(state.so != 0):
                sout.write(f"{lindent}e.so = 0x{state.so}\n")
            if(state.ov != 0):
                sout.write(f"{lindent}e.sv = 0x{state.ov}\n")
            if(state.ca != 0):
                sout.write(f"{lindent}e.ca = 0x{state.ca}\n")


global state_factory
state_factory = {'sim': SimState, 'expected': ExpectedState}


def state_add(name, kls):
    log("state_add", name, kls)
    state_factory[name] = kls


def TestState(state_type, to_test, dut, code=0):
    """TestState: Factory that returns a TestState object loaded with
    registers and memory that can then be compared.

    state_type: Type of state to create from global state_factory dictionary
    to_test: The Power ISA object to test
    dut: The unittest object
    code: Actual machine code of what is being tested

    The state_type can be added to the factory types using the state_add
    function in this module.
    """
    state_class = state_factory[state_type]
    state = state_class(to_test)
    state.to_test = to_test
    state.dut = dut
    state.state_type = state_type
    state.code = code
    yield from state.get_state()
    return state


def teststate_check_regs(dut, states, test, code):
    """teststate_check_regs: compares a set of Power ISA objects
    to check if they have the same "state" (registers only, at the moment)
    """
    slist = []
    # create one TestState per "thing"
    for stype, totest in states.items():
        state = yield from TestState(stype, totest, dut, code)
        slist.append(state)
    # compare each "thing" against the next "thing" in the list.
    # (no need to do an O(N^2) comparison here, they *all* have to be the same
    for i in range(len(slist)-1):
        state, against = slist[i], slist[i+1]
        state.compare(against)


def teststate_check_mem(dut, states, test, code):
    """teststate_check_mem: compares a set of Power ISA objects
    to check if they have the same "state" (memory)
    """
    slist = []
    # create one TestState per "thing"
    for stype, totest in states.items():
        state = yield from TestState(stype, totest, dut, code)
        slist.append(state)
    # compare each "thing" against the next "thing" in the list.
    # (no need to do an O(N^2) comparison here, they *all* have to be the same
    for i in range(len(slist)-1):
        state, against = slist[i], slist[i+1]
        state.compare_mem(against)

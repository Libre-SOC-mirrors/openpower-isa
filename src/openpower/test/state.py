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


class State:
    def get_state(self):
        yield from self.get_intregs()
        yield from self.get_crregs()
        yield from self.get_xregs()
        yield from self.get_pc()

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


class SimState(State):
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


class ExpectedState(State):
    def __init__(self, intregs, pc, crregs, so, ov, ca):
        self.intregs = intregs
        self.pc = pc
        self.crregs = crregs
        self.so = so
        self.ov = ov
        self.ca = ca

    def get_intregs(self):
        if False:
            yield

    def get_crregs(self):
        if False:
            yield

    def get_xregs(self):
        if False:
            yield

    def get_pc(self):
        if False:
            yield


global state_factory
state_factory = {'sim': SimState, 'expected': ExpectedState}


def state_add(name, kls):
    log("state_add", name, kls)
    state_factory[name] = kls


def TestState(state_type, to_test, dut, code):
    state_class = state_factory[state_type]
    state = state_class(to_test)
    state.to_test = to_test
    state.dut = dut
    state.state_type = state_type
    state.code = code
    yield from state.get_state()
    return state

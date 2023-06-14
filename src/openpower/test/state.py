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


from openpower.decoder.power_enums import XER_bits, SPRfull
from openpower.decoder.isa.radixmmu import RADIX
from openpower.util import log
from openpower.fpscr import FPSCRState
from openpower.decoder.selectable_int import SelectableInt
from openpower.consts import DEFAULT_MSR
import os
import sys
from copy import deepcopy

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


class StateSPRs:
    KEYS = tuple(i for i in SPRfull if i != SPRfull.XER)
    __EMPTY_VALUES = {k: 0 for k in KEYS}

    def __init__(self, values=None):
        if isinstance(values, StateSPRs):
            self.__values = values.__values.copy()
            return
        self.__values = self.__EMPTY_VALUES.copy()
        if values is not None:
            for k, v in values.items():
                self[k] = v

    @staticmethod
    def __key(k, raise_if_invalid=True):
        try:
            if isinstance(k, str):
                retval = SPRfull.__members__[k]
            else:
                retval = SPRfull(k)
        except (ValueError, KeyError):
            retval = None
        if retval == SPRfull.XER:  # XER is not stored in StateSPRs
            retval = None
        if retval is None and raise_if_invalid:
            raise KeyError(k)
        return retval

    def items(self):
        for k in StateSPRs.KEYS:
            yield (k, self[k])

    def __iter__(self):
        return iter(StateSPRs.KEYS)

    def __len__(self):
        return len(StateSPRs.KEYS)

    def __contains__(self, k):
        return self.__key(k, raise_if_invalid=False) is not None

    def __getitem__(self, k):
        return self.__values[self.__key(k)]

    def __setitem__(self, k, v):
        k = self.__key(k)
        if v is not None:
            v = int(v)
        self.__values[k] = v

    def nonzero(self):
        return {k: v for k, v in self.__values.items() if v != 0}

    def __repr__(self):
        return repr(self.nonzero())


class State:
    """State: Base class for the "state" of the Power ISA object to be tested
    including methods to compare various registers and memory between
    them.

    All methods implemented must be generators.

    GPRs and CRs - stored as lists
    XERs/PC - simple members
        SO/CA[32]/OV[32] are stored in so/ca/ov members,
        xer_other is all other XER bits.
    SPRs - stored in self.sprs as a StateSPRs
    memory - stored as a dictionary {location: data}
    """

    @property
    def sprs(self):
        return self.__sprs

    @sprs.setter
    def sprs(self, value):
        self.__sprs = StateSPRs(value)

    def get_state(self):
        yield from self.get_fpscr()
        yield from self.get_fpregs()
        yield from self.get_intregs()
        yield from self.get_crregs()
        yield from self.get_xregs()
        yield from self.get_pc()
        yield from self.get_msr()
        yield from self.get_sprs()
        yield from self.get_mem()

    def compare(self, s2):
        # Compare FP registers
        for i, (fpreg, fpreg2) in enumerate(
                zip(self.fpregs, s2.fpregs)):
            log("asserting...reg", i, fpreg, fpreg2)
            log("code, frepr(code)", self.code, repr(self.code))
            self.dut.assertEqual(fpreg, fpreg2,
                "fp reg %d (%s) not equal (%s) %s. "
                " got %x  expected %x at pc %x %x\n" %
                (i, self.state_type, s2.state_type, repr(self.code),
                fpreg, fpreg2, self.pc, s2.pc))

        # Compare int registers
        for i, (intreg, intreg2) in enumerate(
                zip(self.intregs, s2.intregs)):
            log("asserting...reg", i, intreg, intreg2)
            log("code, frepr(code)", self.code, repr(self.code))
            self.dut.assertEqual(intreg, intreg2,
                "int reg %d (%s) not equal (%s) %s. "
                " got %x  expected %x at pc %x %x\n" %
                (i, self.state_type, s2.state_type, repr(self.code),
                intreg, intreg2, self.pc, s2.pc))

        # CR registers
        for i, (crreg, crreg2) in enumerate(
                zip(self.crregs, s2.crregs)):
            log("asserting...cr", i, crreg, crreg2)

        for i, (crreg, crreg2) in enumerate(
                zip(self.crregs, s2.crregs)):
            self.dut.assertEqual(crreg, crreg2,
                "cr reg %d (%s) not equal (%s) %s. got %x  expected %x" %
                (i, self.state_type, s2.state_type, repr(self.code),
                crreg, crreg2))

        # XER
        if self.so is not None and s2.so is not None:
            self.dut.assertEqual(self.so, s2.so, "so mismatch (%s != %s) %s" %
                (self.state_type, s2.state_type, repr(self.code)))
        if self.ov is not None and s2.ov is not None:
            self.dut.assertEqual(self.ov, s2.ov, "ov mismatch (%s != %s) %s" %
                (self.state_type, s2.state_type, repr(self.code)))
        if self.ca is not None and s2.ca is not None:
            self.dut.assertEqual(self.ca, s2.ca, "ca mismatch (%s != %s) %s" %
                (self.state_type, s2.state_type, repr(self.code)))
        if self.xer_other is not None and s2.xer_other is not None:
            self.dut.assertEqual(
                hex(self.xer_other), hex(s2.xer_other),
                "xer_other mismatch (%s != %s) %s" %
                (self.state_type, s2.state_type, repr(self.code)))

        # pc
        self.dut.assertEqual(self.pc, s2.pc, "pc mismatch (%s != %s) %s" %
            (self.state_type, s2.state_type, repr(self.code)))

        # fpscr
        if self.fpscr is not None and s2.fpscr is not None:
            if self.fpscr != s2.fpscr:
                # use FPSCRState.fsi since that's much easier to read than a
                # decimal integer and since unittest has fancy dict diffs.

                # use auto_update_summary_bits=False since HDL might
                # mis-compute those summary bits and we want to show the
                # actual bits, not the corrected bits
                fpscr1 = FPSCRState(self.fpscr, auto_update_summary_bits=False)
                fpscr2 = FPSCRState(s2.fpscr, auto_update_summary_bits=False)
                # FieldSelectableInt.__repr__ is too long
                fpscr1 = {k: hex(int(v)) for k, v in fpscr1.fsi.items()}
                fpscr2 = {k: hex(int(v)) for k, v in fpscr2.fsi.items()}
                old_max_diff = self.dut.maxDiff
                self.dut.maxDiff = None  # show full diff
                try:
                    self.dut.assertEqual(
                        fpscr1, fpscr2, "fpscr mismatch (%s != %s) %s\n" %
                        (self.state_type, s2.state_type, repr(self.code)))
                finally:
                    self.dut.maxDiff = old_max_diff

        for spr in self.sprs:
            spr1 = self.sprs[spr]
            spr2 = s2.sprs[spr]

            if spr1 == spr2:
                continue

            if spr1 is not None and spr2 is not None:
                # if not explicitly ignored

                self.dut.fail(
                    f"{spr1:#x} != {spr2:#x}: {spr} mismatch "
                    f"({self.state_type} != {s2.state_type}) {self.code!r}\n")

        if self.msr is not None and s2.msr is not None:
            self.dut.assertEqual(
                hex(self.msr), hex(s2.msr), "msr mismatch (%s != %s) %s" %
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

    def dump_state_tofile(self, testname=None, testfile=None):
        """dump_state_tofile:  Takes a passed in teststate object along
        with a test name and generates a code file located at
        /tmp/testfile/testname to set an expected state object
        """
        lindent = ' '*8 # indent for code
        # create the path
        if testname is not None:
            path = "/tmp/expected/"
            if testfile is not None:
                path += testfile + '/'
            os.makedirs(path, exist_ok=True)
            sout = open("%s%s.py" % (path, testname), "a+")
        else:
            sout = sys.stdout

        # pc and intregs
        sout.write("%se = ExpectedState(pc=%d)\n" % (lindent, self.pc))
        for i, reg in enumerate(self.intregs):
            if(reg != 0):
                msg = "%se.intregs[%d] = 0x%x\n"
                sout.write( msg % (lindent, i, reg))
        for i, reg in enumerate(self.fpregs):
            if reg != 0:
                msg = "%se.fpregs[%d] = 0x%x\n"
                sout.write(msg % (lindent, i, reg))
        # CR fields
        for i in range(8):
            cri = self.crregs[i]
            if(cri != 0):
                msg = "%se.crregs[%d] = 0x%x\n"
                sout.write( msg % (lindent, i, cri))
        # XER
        if(self.so != 0):
            sout.write("%se.so = 0x%x\n" % (lindent, self.so))
        if(self.ov != 0):
            sout.write("%se.ov = 0x%x\n" % (lindent, self.ov))
        if(self.ca != 0):
            sout.write("%se.ca = 0x%x\n" % (lindent, self.ca))
        if self.xer_other != 0:
            sout.write("%se.xer_other = 0x%x\n" % (lindent, self.xer_other))

        # FPSCR
        if self.fpscr != 0:
            sout.write(f"{lindent}e.fpscr = {self.fpscr:#x}\n")

        # SPRs
        for k, v in self.sprs.nonzero().items():
            sout.write(f"{lindent}e.sprs[{k.name!r}] = {v:#x}\n")

        # MSR
        if self.msr != 0:
            sout.write(f"{lindent}e.msr = {self.msr:#x}\n")

        if sout != sys.stdout:
            sout.close()


def _get_regs(regs, asint=lambda v: v.asint()):
    retval = []
    while True:
        try:
            retval.append(asint(regs[len(retval)]))
        except (IndexError, KeyError):
            break
    return retval


class SimState(State):
    """SimState: Obtains registers and memory from an ISACaller object.
    Note that yields are "faked" to maintain consistency and compatibility
    within the API.
    """
    def __init__(self, sim):
        self.sim = sim

    def get_fpregs(self):
        if False:
            yield
        self.fpregs = _get_regs(self.sim.fpr)
        log("class sim fp regs", list(map(hex, self.fpregs)))

    def get_fpscr(self):
        if False:
            yield
        self.fpscr = int(self.sim.fpscr)
        log("class sim fpscr", hex(self.fpscr))

    def get_msr(self):
        if False:
            yield
        self.msr = int(self.sim.msr)
        log("class sim msr", hex(self.msr))

    def get_intregs(self):
        if False:
            yield
        self.intregs = _get_regs(self.sim.gpr)
        log("class sim int regs", list(map(hex, self.intregs)))

    def get_crregs(self):
        if False:
            yield
        self.crregs = _get_regs(self.sim.crl, lambda v: v.get_range().value)
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
        xer_other = SelectableInt(self.sim.spr['XER'])
        for i in 'SO', 'OV', 'OV32', 'CA', 'CA32':
            xer_other[XER_bits[i]] = 0
        self.xer_other = int(xer_other)
        self.xregs.extend((self.so, self.ov, self.ca))
        log("class sim xregs", list(map(hex, self.xregs)))

    def get_sprs(self):
        if False:
            yield
        self.sprs = StateSPRs()
        for spr in self.sprs:
            # hacky workaround to workaround luke's hack in caller.py that
            # aliases HSRR[01] to SRR[01] -- we temporarily clear SRR[01] while
            # trying to read HSRR[01]
            clear_srr = spr == SPRfull.HSRR0 or spr == SPRfull.HSRR1
            if clear_srr:
                old_srr0 = self.sim.spr['SRR0']
                old_srr1 = self.sim.spr['SRR1']
                self.sim.spr['SRR0'] = 0
                self.sim.spr['SRR1'] = 0

            self.sprs[spr] = self.sim.spr[spr.name]  # setitem converts to int

            if clear_srr:
                self.sim.spr['SRR0'] = old_srr0
                self.sim.spr['SRR1'] = old_srr1

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
        mem = self.sim.mem
        if isinstance(mem, RADIX):
            mem = mem.mem
        keys = list(mem.mem.keys())
        self.mem = {}
        # from each address in the underlying mem-simulated dictionary
        # issue a 64-bit LD (with no byte-swapping)
        for k in keys:
            data = mem.ld(k*8, 8, False)
            self.mem[k*8] = data


class ExpectedState(State):
    """ExpectedState: A user defined state set manually.
    No methods, just pass into what expected values you want to test
    with against other states.

    see openpower/test/shift_rot/shift_rot_cases2.py for examples
    """
    def __init__(self, int_regs=None, pc=0, crregs=None,
                 so=0, ov=0, ca=0, fp_regs=None, fpscr=0, sprs=None,
                 msr=DEFAULT_MSR, xer_other=0):
        if fp_regs is None:
            fp_regs = 32
        if isinstance(fp_regs, int):
            fp_regs = [0] * fp_regs
        self.fpregs = deepcopy(fp_regs)
        self.fpscr = fpscr
        if int_regs is None:
            int_regs = 32
        if isinstance(int_regs, int):
            int_regs = [0] * int_regs
        self.intregs = deepcopy(int_regs)
        self.pc = pc
        if crregs is None:
            crregs = 8
        if isinstance(crregs, int):
            crregs = [0] * crregs
        self.crregs = deepcopy(crregs)
        self.so = so
        self.ov = ov
        self.ca = ca
        self.xer_other = xer_other
        self.sprs = StateSPRs(sprs)
        self.msr = msr

    def get_fpregs(self):
        if False: yield
    def get_fpscr(self):
        if False: yield
    def get_intregs(self):
        if False: yield
    def get_crregs(self):
        if False: yield
    def get_xregs(self):
        if False: yield
    def get_pc(self):
        if False: yield

    def get_msr(self):
        if False:
            yield

    def get_sprs(self):
        if False:
            yield

    def get_mem(self):
        if False: yield


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

from nmigen import Module, Signal
from nmigen.sim import Simulator, Settle
from openpower.decoder.isa.caller import ISACaller
from openpower.decoder.power_decoder import create_pdecode
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import ISACaller, inject
from openpower.decoder.isa.all import ISA
from openpower.test.state import TestState
from nmutil.formaltest import FHDLTestCase


class Register:
    def __init__(self, num):
        self.num = num


class ISATestRunner(FHDLTestCase):
    def __init__(self, tst_data, include_fp=True):
        super().__init__("run_all")
        self.test_data = tst_data
        self.include_fp = include_fp

    def run_all(self):
        m = Module()
        comb = m.d.comb
        instruction = Signal(32)

        pdecode = create_pdecode(include_fp=self.include_fp)
        m.submodules.pdecode2 = pdecode2 = PowerDecode2(pdecode)

        comb += pdecode2.dec.raw_opcode_in.eq(instruction)
        sim = Simulator(m)

        def process():

            for test in self.test_data:

                with self.subTest(test.name):
                    generator = test.program

                    gen = list(generator.generate_instructions())
                    insncode = generator.assembly.splitlines()
                    instructions = list(zip(gen, insncode))

                    simulator = ISA(pdecode2, test.regs,
                                    test.sprs,
                                    test.cr,
                                    initial_insns=gen, respect_pc=True,
                                    initial_svstate=test.svstate,
                                    initial_mem=test.mem,
                                    fpregfile=None,
                                    disassembly=insncode,
                                    bigendian=0,
                                    mmu=False)

                    print ("GPRs")
                    simulator.gpr.dump()
                    print ("FPRs")
                    simulator.fpr.dump()

                    yield pdecode2.dec.bigendian.eq(0)  # little / big?
                    pc = simulator.pc.CIA.value
                    index = pc//4
                    while index < len(instructions):
                        print("instr pc", pc)
                        try:
                            yield from simulator.setup_one()
                        except KeyError:  # instruction not in imem: stop
                            break
                        yield Settle()

                        ins, code = instructions[index]
                        print("    0x{:X}".format(ins & 0xffffffff))
                        opname = code.split(' ')[0]
                        print(code, opname)

                        # ask the decoder to decode this binary data (endian'd)
                        yield from simulator.execute_one()
                        pc = simulator.pc.CIA.value
                        index = pc//4

        # run simulator multiple times, using the same PowerDecoder2,
        # with multiple sub-tests
        sim.add_process(process)
        with sim.write_vcd("simulator.vcd", "simulator.gtkw",
                           traces=[]):
            sim.run()


def check_regs(dut, sim, expected, test, code):
    # create the two states and compare
    testdic = {'sim': sim, 'expected': expected}
    yield from teststate_check_regs(dut, testdic, test, code)


def run_tst(generator, initial_regs, initial_sprs=None, svstate=0, mmu=False,
                                     initial_cr=0, mem=None,
                                     initial_fprs=None,
                                     pdecode2=None,
                                     state=None): # (dut, code)
    if initial_sprs is None:
        initial_sprs = {}
    m = Module()
    comb = m.d.comb
    instruction = Signal(32)

    if pdecode2 is None:
        pdecode = create_pdecode(include_fp=initial_fprs is not None)
        pdecode2 = PowerDecode2(pdecode)
    m.submodules.pdecode2 = pdecode2

    gen = list(generator.generate_instructions())
    insncode = generator.assembly.splitlines()
    instructions = list(zip(gen, insncode))

    simulator = ISA(pdecode2, initial_regs, initial_sprs, initial_cr,
                    initial_insns=gen, respect_pc=True,
                    initial_svstate=svstate,
                    initial_mem=mem,
                    fpregfile=initial_fprs,
                    disassembly=insncode,
                    bigendian=0,
                    mmu=mmu)
    comb += pdecode2.dec.raw_opcode_in.eq(instruction)
    sim = Simulator(m)

    process_state = state

    def process():

        print ("GPRs")
        simulator.gpr.dump()
        print ("FPRs")
        simulator.fpr.dump()

        yield pdecode2.dec.bigendian.eq(0)  # little / big?
        pc = simulator.pc.CIA.value
        index = pc//4
        while index < len(instructions):
            print("instr pc", pc)
            try:
                yield from simulator.setup_one()
            except KeyError:  # indicates instruction not in imem: stop
                break
            yield Settle()

            ins, code = instructions[index]
            print("    0x{:X}".format(ins & 0xffffffff))
            opname = code.split(' ')[0]
            print(code, opname)

            # ask the decoder to decode this binary data (endian'd)
            yield from simulator.execute_one()
            pc = simulator.pc.CIA.value
            index = pc//4

        # use this to test against expected (static) results at end of run
        if process_state is not None:
            (dut, code) = process_state
            simulator.state = yield from TestState("sim", simulator, dut, code)

    sim.add_process(process)
    with sim.write_vcd("simulator.vcd", "simulator.gtkw",
                       traces=[]):
        sim.run()

    return simulator



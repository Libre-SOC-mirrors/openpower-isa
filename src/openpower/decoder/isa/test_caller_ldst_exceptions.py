from nmigen import Module, Signal
from nmigen.back.pysim import Simulator, Delay, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.isa.caller import ISACaller
from openpower.decoder.power_decoder import (create_pdecode)
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import ISACaller, inject
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.all import ISA
from openpower.consts import PIb


class Register:
    def __init__(self, num):
        self.num = num

def run_tst(generator, initial_regs, initial_sprs=None, svstate=0, mmu=False,
                                     initial_cr=0,mem=None):
    if initial_sprs is None:
        initial_sprs = {}
    m = Module()
    comb = m.d.comb
    instruction = Signal(32)

    pdecode = create_pdecode()

    gen = list(generator.generate_instructions())
    insncode = generator.assembly.splitlines()
    instructions = list(zip(gen, insncode))

    m.submodules.pdecode2 = pdecode2 = PowerDecode2(pdecode)
    simulator = ISA(pdecode2, initial_regs, initial_sprs, initial_cr,
                    initial_insns=gen, respect_pc=True,
                    initial_svstate=svstate,
                    initial_mem=mem,
                    disassembly=insncode,
                    bigendian=0,
                    mmu=mmu)
    comb += pdecode2.dec.raw_opcode_in.eq(instruction)
    sim = Simulator(m)


    def process():

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

    sim.add_process(process)
    with sim.write_vcd("simulator.vcd", "simulator.gtkw",
                       traces=[]):
        sim.run()
    return simulator


class DecoderTestCase(FHDLTestCase):

    def test_load_misalign(self):
        lst = ["addi 2, 0, 0x0010", # get PC off of zero
               "ldx 3, 0, 1",
               ]
        initial_regs = [0] * 32
        all1s = 0xFFFFFFFFFFFFFFFF
        initial_regs[1] = all1s
        initial_regs[2] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, initial_mem)
            self.assertEqual(sim.gpr(1), SelectableInt(all1s, 64))
            self.assertEqual(sim.gpr(3), SelectableInt(0, 64))
            print ("DAR", hex(sim.spr['DAR'].value))
            print ("PC", hex(sim.pc.CIA.value))
            # TODO get MSR, test that.
            # TODO, test rest of SRR1 equal to zero
            self.assertEqual(sim.spr['SRR1'][PIb.PRIV], 0x1) # expect priv bit
            self.assertEqual(sim.spr['SRR0'], 0x4)   # expect to be 2nd op
            self.assertEqual(sim.spr['DAR'], all1s)   # expect failed LD addr
            self.assertEqual(sim.pc.CIA.value, 0x600) # align exception

    def run_tst_program(self, prog, initial_regs=[0] * 32, initial_mem=None):
        simulator = run_tst(prog, initial_regs, mem=initial_mem)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()

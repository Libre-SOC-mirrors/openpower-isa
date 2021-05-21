from nmigen import Module, Signal
from nmigen.back.pysim import Simulator, Delay, Settle
import string
import sys
import getopt
from openpower.decoder.power_decoder import create_pdecode
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.all import ISA


def convert_to_num(num):
    # detect number types
    if num.isdigit():
        return int(reg)
    if num.startswith("0b"):
        return int(value[2], 2)
    if value.startswith("0x"):
        return int(value[2], 16)
    return num


def read_entries(fname, listqty=None):
    """read_entries: reads values from a file of the format "x: y", per line
    can be used for memory, or regfiles (GPR, SPR, FP).  regs and entries may
    start with "0x" or "0b" for hex or binary
    """
    regs = {}
    with open(fname) as f:
        for line in f.readlines():
            # split line "x : y" into ["x", "y"], remove spaces
            line = map(string.strip, line.strip().split(":"))
            assert len(line) == 2, "regfile line must be formatted 'x : y'"
            reg, val = line
            reg = convert_to_num(reg)
            val = convert_to_num(val)
            assert reg not in regs, "duplicate entry %s" % (repr(reg))
            regs[reg] = val

    # post-process into a list.
    if listqty is None:
        return regs
    result = [0] * listqty
    for reg, value in regs.items():
        assert isinstance(reg, int), "list must be int, %s found" % reg
        assert reg < listqty, "entry %s too large for list %s" % (reg, listqty)
        result[reg] = value

    return result


def run_tst(args, generator, initial_regs, 
                             initial_sprs=None, svstate=0, mmu=False,
                             initial_cr=0, mem=None,
                             initial_fprs=None):
    if initial_regs is None:
        initial_regs = [0] * 32
    if initial_sprs is None:
        initial_sprs = {}

    m = Module()
    comb = m.d.comb
    instruction = Signal(32)

    pdecode = create_pdecode(include_fp=initial_fprs is not None)

    gen = list(generator.generate_instructions())
    insncode = generator.assembly.splitlines()
    instructions = list(zip(gen, insncode))

    m.submodules.pdecode2 = pdecode2 = PowerDecode2(pdecode)
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
    sim.run()

    return simulator


if __name__ == "__main__":

    binaryname = None
    initial_regs = None
    lst = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:l:g:f:", 
                                   ["binary", "listing",
                                    "intregs"])
      
    except:
        sys.stderr.write("Command-line Error\n")
        exit(-1)

    for opt, arg in opts:
        if opt in ['-i', '--binary']:
            binaryname = arg
        elif opt in ['-l', '--listing']:
            lst = arg
        elif opt in ['g', '--intregs']:
            initial_regs = read_entries(arg, 32)

    if binaryname is None and lst is None:
        sys.stderr.write("Must give binary or listing\n")
        exit(-1)

    if lst:
        with open(lst, "r") as f:
            lst = list(f.readlines())

    if binaryname:
        with open(binaryname, "rb") as f:
            lst = f.read()

    with Program(lst, bigendian=False) as prog:
        simulator = run_tst(None, prog,
                            initial_regs,
                            initial_sprs=None, svstate=0, mmu=False,
                            initial_cr=0, mem=None,
                            initial_fprs=None)
        simulator.gpr.dump()
        simulator.fpr.dump()

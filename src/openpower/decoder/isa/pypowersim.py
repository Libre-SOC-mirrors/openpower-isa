from nmigen import Module, Signal
from nmigen.back.pysim import Simulator, Delay, Settle
import sys
import getopt
import struct
from openpower.decoder.power_decoder import create_pdecode
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.all import ISA


def read_data(fname, offset=0):
    """reads binary data and returns a dictionary of address: contents,
    each entry is 8 bytes. input file *must* be 8-byte-aligned
    """
    res = {}
    with open(fname, "rb") as f:
        while True:
            b = f.read(8)
            print (repr(b))
            if not b:
                return res
            res[offset] = struct.unpack('<Q', b)[0] # unsigned long
            offset += 8

def write_data(mem, fname, offset, sz):
    """writes binary data to a file, each entry must be 8 bytes
    """
    with open(fname, "wb") as f:
        for i in range(0, sz, 8):
            addr = offset + i
            val = mem.ld(addr, 8)
            f.write(struct.pack('<Q', val)) # unsigned long


def convert_to_num(num):
    # detect number types
    if num.isdigit():
        return int(num)
    if num.startswith("0b"):
        return int(num[2:], 2)
    if num.startswith("0x"):
        return int(num[2:], 16)
    return num


def read_entries(fname, listqty=None):
    """read_entries: reads values from a file of the format "x: y", per line
    can be used for memory, or regfiles (GPR, SPR, FP).  regs and entries may
    start with "0x" or "0b" for hex or binary
    """
    regs = {}
    allints = True
    with open(fname) as f:
        for line in f.readlines():
            # split line "x : y" into ["x", "y"], remove spaces
            line = list(map(str.strip, line.strip().split(":")))
            assert len(line) == 2, "regfile line must be formatted 'x : y'"
            # check and convert format
            reg, val = line
            reg = convert_to_num(reg)
            val = convert_to_num(val)
            assert reg not in regs, "duplicate entry %s" % (repr(reg))
            allints = allints and isinstance(reg, int)
            regs[reg] = val

    # SPRs can be named
    if not allints:
        return regs

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
    print ("instructions gen", gen)
    insncode = generator.assembly.splitlines()
    if insncode:
        instructions = list(zip(gen, insncode))
    else:
        instructions = gen

    print ("instructions", instructions)

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
        while index < len(instructions) and not simulator.halted:
            print("instr pc", pc)
            try:
                yield from simulator.setup_one()
            except KeyError:  # indicates instruction not in imem: stop
                break
            yield Settle()

            ins = instructions[index]
            if isinstance(ins, list):
                ins, code = ins
                print("    0x{:X}".format(ins & 0xffffffff))
                opname = code.split(' ')[0]
                print(code, opname)
            else:
                print("    0x{:X}".format(ins & 0xffffffff))

            # ask the decoder to decode this binary data (endian'd)
            yield from simulator.execute_one()
            pc = simulator.pc.CIA.value
            index = pc//4

    sim.add_process(process)
    sim.run()

    return simulator


def help():
    print ("-i --binary=   raw (non-ELF) bare metal executable, loaded at 0x0")
    print ("-l --listing=  file containing bare-metal assembler (no macros)")
    print ("-g --intregs=  colon-separated file with GPR values")
    print ("-f --fpregs=   colon-separated file with FPR values")
    print ("-s --spregs=   colon-separated file with SPR values")
    print ("-l --load=     filename:address to load binary into memory")
    print ("-d --dump=     filename:address:len to binary save from memory")
    print ("-h --help      prints this message")
    print ("load and dump may be given multiple times")
    exit(-1)


def run_simulation():

    binaryname = None
    initial_regs = [0]*32
    initial_fprs = [0]*32
    initial_sprs = None
    initial_mem = {}
    lst = None
    write_to = []

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:l:g:f:s:l:d:",
                                   ["help",
                                    "binary=", "listing=",
                                    "intregs=", "fpregs=", "sprs=",
                                    "load=", "dump="])

    except:
        sys.stderr.write("Command-line Error\n")
        help()

    for opt, arg in opts:
        if opt in ['-h', '--help']:
            help()
        elif opt in ['-i', '--binary']:
            binaryname = arg
        elif opt in ['-l', '--listing']:
            lst = arg
        elif opt in ['-g', '--intregs']:
            initial_regs = read_entries(arg, 32)
        elif opt in ['-f', '--fpregs']:
            initial_fprs = read_entries(arg, 32)
        elif opt in ['-s', '--sprs']:
            initial_sprs = read_entries(arg, 32)
        elif opt in ['-l', '--load']:
            arg = list(map(str.strip, arg.split(":")))
            if len(arg) == 1:
                fname, offs = arg[0], 0
            else:
                fname, offs = arg
            offs = convert_to_num(offs)
            print ("offs load", fname, offs)
            mem = read_data(fname, offs)
            initial_mem.update(mem)
        elif opt in ['-d', '--dump']:
            arg = list(map(str.strip, arg.split(":")))
            assert len(arg) == 3, \
                   "dump '%s' must contain file:offset:length" % repr(arg)
            fname, offs, length = arg
            offs = convert_to_num(offs)
            length = convert_to_num(length)
            assert length % 8 == 0, "length %d must align on 8-byte" % length
            print ("dump", fname, offs, length)
            write_to.append((fname, offs, length))

    print (initial_mem)

    if binaryname is None and lst is None:
        sys.stderr.write("Must give binary or listing\n")
        help()

    if lst:
        with open(lst, "r") as f:
            lst = list(map(str.strip, f.readlines()))

    if binaryname:
        with open(binaryname, "rb") as f:
            lst = f.read()

    with Program(lst, bigendian=False) as prog:
        simulator = run_tst(None, prog,
                            initial_regs,
                            initial_sprs=initial_sprs,
                            svstate=0, mmu=False,
                            initial_cr=0, mem=initial_mem,
                            initial_fprs=initial_fprs)
        print ("GPRs")
        simulator.gpr.dump()
        print ("FPRs")
        simulator.fpr.dump()
        print ("SPRs")
        simulator.spr.dump()
        print ("Mem")
        simulator.mem.dump()

        for fname, offs, length in write_to:
            write_data(simulator.mem, fname, offs, length)


if __name__ == "__main__":
    run_simulation()


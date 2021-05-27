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
from openpower.util import log
from openpower.simulator.qemu import run_program


def read_data(fname, offset=0):
    """reads binary data and returns a dictionary of address: contents,
    each entry is 8 bytes: input file *must* contain a multiple of 8 bytes.
    data to be considered *binary* (raw)
    """
    res = {}
    with open(fname, "rb") as f:
        while True:
            b = f.read(8)
            log (repr(b))
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
            f.write(struct.pack('>Q', val)) # unsigned long


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
            # split out comments
            if line.startswith("#"):
                continue
            line = line.split("#")[0]
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

def qemu_register_compare(sim, q, regs, fprs):
    qpc, qxer, qcr, qlr = q.get_pc(), q.get_xer(), q.get_cr(), q.get_lr()
    sim_cr = sim.cr.value
    sim_pc = sim.pc.CIA.value
    sim_xer = sim.spr['XER'].value
    sim_lr = sim.spr['LR'].value
    print("qemu pc", hex(qpc))
    print("qemu cr", hex(qcr))
    print("qemu lr", hex(qlr))
    print("qemu xer", bin(qxer))
    print("sim nia", hex(sim.pc.NIA.value))
    print("sim pc", hex(sim.pc.CIA.value))
    print("sim cr", hex(sim_cr))
    print("sim xer", hex(sim_xer))
    print("sim lr", hex(sim_lr))
    #self.assertEqual(qpc, sim_pc)
    for reg in regs:
        qemu_val = q.get_gpr(reg)
        sim_val = sim.gpr(reg).value
        if qemu_val != sim_val:
            log("expect gpr %d %x got %x" % (reg, qemu_val, sim_val))
        #self.assertEqual(qemu_val, sim_val,
        #                 "expect %x got %x" % (qemu_val, sim_val))
    for fpr in fprs:
        qemu_val = q.get_fpr(fpr)
        sim_val = sim.fpr(fpr).value
        if qemu_val != sim_val:
            log("expect fpr %d %x got %x" % (fpr, qemu_val, sim_val))
        #self.assertEqual(qemu_val, sim_val,
        #                 "expect %x got %x" % (qemu_val, sim_val))
    #self.assertEqual(qcr, sim_cr)


def run_tst(args, generator, qemu,
                             initial_regs,
                             initial_sprs=None, svstate=0, mmu=False,
                             initial_cr=0, mem=None,
                             initial_fprs=None,
                             initial_pc=0):
    if initial_regs is None:
        initial_regs = [0] * 32
    if initial_sprs is None:
        initial_sprs = {}

    if qemu:
        log("qemu program", generator.binfile.name)
        qemu = run_program(generator, initial_mem=mem, 
                bigendian=False, start_addr=initial_pc,
                continuous_run=False, initial_sprs=initial_sprs)
        if initial_regs is not None:
            for reg, val in enumerate(initial_regs):
                qemu.set_gpr(reg, val)
        if initial_fprs is not None:
            for fpr, val in enumerate(initial_fprs):
                qemu.set_fpr(fpr, val)
        for reg, val in qemu._get_registers().items():
            print (reg, hex(val))

    m = Module()
    comb = m.d.comb
    instruction = Signal(32)

    pdecode = create_pdecode(include_fp=initial_fprs is not None)

    gen = list(generator.generate_instructions())
    log ("instructions gen", gen)
    insncode = generator.assembly.splitlines()
    if insncode:
        instructions = list(zip(gen, insncode))
    else:
        instructions = gen

    log ("instructions", instructions)

    m.submodules.pdecode2 = pdecode2 = PowerDecode2(pdecode)
    simulator = ISA(pdecode2, initial_regs, initial_sprs, initial_cr,
                    initial_insns=(initial_pc, gen), respect_pc=True,
                    initial_svstate=svstate,
                    initial_mem=mem,
                    initial_pc=initial_pc,
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

        # rather awkward: qemu will go wonky if stepped over the
        # last instruction.  use ISACaller to check if this is
        # the last instruction, and leave qemu pointing at it
        # rather than trigger an exception in the remote-qemu program
        try:
            _pc, _ins = simulator.get_next_insn()
        except KeyError:  # indicates instruction not in imem: stop
            return

        while not simulator.halted:
            log("instr pc", pc)
            yield from simulator.setup_next_insn(_pc, _ins)
            yield Settle()

            if False:
                ins = instructions[index]
                if isinstance(ins, list):
                    ins, code = ins
                    log("    0x{:X}".format(ins & 0xffffffff))
                    opname = code.split(' ')[0]
                    log(code, opname)
                else:
                    log("    0x{:X}".format(ins & 0xffffffff))

            # ask the decoder to decode this binary data (endian'd)
            yield from simulator.execute_one()
            #pc = simulator.pc.CIA.value
            #index = pc//4

            if not qemu:
                try:
                    _pc, _ins = simulator.get_next_insn()
                except KeyError:  # indicates instruction not in imem: stop
                    return
                continue

            # check qemu co-sim: run one instruction, but first check
            # in ISACaller if there *is* a next instruction.  if there
            # is, "recover" qemu by switching bigendian back
            try:
                _pc, _ins = simulator.get_next_insn()
            except KeyError:  # indicates instruction not in imem: stop
                _pc, _insn = (None, None)
            qemu.step()
            if not _pc or simulator.halted:
                qemu.set_endian(False)
            qemu_register_compare(simulator, qemu, range(32), range(32))
            if _pc is None:
                break

        # cleanup
        if qemu:
            qemu.exit()

    sim.add_process(process)
    sim.run()

    return simulator


def help():
    print ("-i --binary=   raw (non-ELF) bare metal executable, loaded at 0x0")
    print ("-a --listing=  file containing bare-metal assembler (no macros)")
    print ("-g --intregs=  colon-separated file with GPR values")
    print ("-f --fpregs=   colon-separated file with FPR values")
    print ("-s --spregs=   colon-separated file with SPR values")
    print ("-l --load=     filename:address to load binary into memory")
    print ("-d --dump=     filename:address:len to binary save from memory")
    print ("-q --qemu=     run qemu co-simulation")
    print ("-p --pc=       set initial program counter")
    print ("-h --help      prints this message")
    print ("notes:")
    print ("load and dump may be given multiple times")
    print ("load and dump must be 8-byte aligned sizes")
    print ("loading SPRs accepts SPR names (e.g. LR, CTR, SRR0)")
    print ("numbers may be integer, binary (0bNNN) or hex (0xMMM) but not FP")
    print ("running ELF binaries: load SPRs, LR set to 0xffffffffffffffff")
    print ("TODO: dump registers")
    print ("TODO: load/dump PC, MSR, CR")
    print ("TODO: print exec and sub-exec counters at end")
    exit(-1)


def run_simulation():

    binaryname = None
    initial_regs = [0]*32
    initial_fprs = [0]*32
    initial_sprs = None
    initial_mem = {}
    initial_pc = 0x0
    lst = None
    qemu_cosim = False
    write_to = []

    try:
        opts, args = getopt.getopt(sys.argv[1:], "qhi:a:g:f:s:l:d:p:",
                                   ["qemu", "help", "pc=",
                                    "binary=", "listing=",
                                    "intregs=", "fpregs=", "sprs=",
                                    "load=", "dump="])

    except:
        sys.stderr.write("Command-line Error\n")
        help()

    for opt, arg in opts:
        if opt in ['-h', '--help']:
            help()
        elif opt in ['-q', '--qemu']:
            qemu_cosim = True
        elif opt in ['-i', '--binary']:
            binaryname = arg
        elif opt in ['-p', '--pc']:
            initial_pc = convert_to_num(arg)
        elif opt in ['-a', '--listing']:
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
            log ("offs load", fname, offs)
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
            log ("dump", fname, offs, length)
            write_to.append((fname, offs, length))

    log (initial_mem)

    if binaryname is None and lst is None:
        sys.stderr.write("Must give binary or listing\n")
        help()

    if lst:
        with open(lst, "r") as f:
            lst = list(map(str.strip, f.readlines()))

    if binaryname:
        with open(binaryname, "rb") as f:
            lst = f.read()

    with Program(lst, bigendian=False, orig_filename=binaryname) as prog:
        simulator = run_tst(None, prog, qemu_cosim,
                            initial_regs,
                            initial_sprs=initial_sprs,
                            svstate=0, mmu=False,
                            initial_cr=0, mem=initial_mem,
                            initial_fprs=initial_fprs,
                            initial_pc=initial_pc)
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


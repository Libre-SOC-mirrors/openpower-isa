#!/usr/bin/env python3
# An In-order cycle-accurate model of a Power ISA 3.0 hardware implementation
# LGPLv3+
# Funded by NLnet
#
# Bugs: https://bugs.libre-soc.org/show_bug.cgi?id=1039
"""
    CPU:   Fetch   <- log file
            |
           Decode  <- works out read/write regs
            |
           Issue   <- checks read-regs, sets write-regs
            |
           Execute  -> stages (countdown) clears write-regs

"""

from collections import namedtuple
import io
import unittest

# trace file entries are lists of these.
Hazards = namedtuple("Hazards", ["action", "target", "ident", "offs", "elwid"])

# key: readport, writeport (per clock cycle)
HazardProfiles = {
    "GPR": (4, 1),  # GPR allows 4 reads 1 write possible in 1 cycle...
    "FPR": (3, 1),
    "CR" : (2, 1),  # Condition Register (32-bit)
    "CRf": (3, 3),  # Condition Register Fields (4-bit each)
    "XER": (1, 1),
    "MSR": (1, 1),
    "FPSCR": (1, 1),
    "PC": (1, 1),    # Program Counter
    "SPRf" : (4, 3), # Fast SPR (actually STATE regfile in TestIssuer)
    "SPRs" : (1, 1), # Slow SPR
}


def read_file(fname):
    """reads a trace file in the format "[r:FILE:regnum:offset:width]* # insn"
    """
    is_file = hasattr(fname, "write")
    if not is_file:
        fname = open(fname, "r")
    res = []
    for line in fname.readlines():
        (specs, insn) = map(str.strip, line.strip().split("#"))
        line = [insn]
        for spec in specs.split(" "):
            line.append(Hazards._make(spec.split(":")))
        res.append(line)
    if not is_file:
        fname.close()
    return res


class RegisterWrite:
    """
    RegisterWrite: contains the set of Read-after-Write Hazards.
    Anything in this set must be a STALL at Decode phase because the
    answer has still not popped out the end of a pipeline
    """
    def __init__(self):
        self.storage = set()

    def expect_write(self, regs):
        return self.storage.update(regs)

    def write_expected(self, regs):
        return (len(self.storage.intersection(regs)) != 0)

    def retire_write(self, regs):
        return self.storage.difference_update(regs)


class Execute:
    """
    Execute Pipeline: keeps a countdown-sorted list of instructions
    to expect at a future cycle (tick).  Anything at zero is processed
    by assuming it is completed, and wishes to write to the regfile.
    However there are only a limited number of regfile write ports,
    so they must be handled a few at a time.  under these circumstances
    STALL condition is returned, and the "processor" must *NOT* tick().
    """
    def __init__(self, cpu):
        self.stages = []
        self.cpu = cpu

    def add_stage(self, cycles_away, stage):
        while cycles_away > len(self.stages):
            self.stages.append([])
        self.stages[cycles_away].append(stage)

    def add_instruction(self, insn, writeregs):
        self.add_stage(2, {'insn': insn, 'writes': writeregs})

    def tick(self):
        self.stages.pop(0) # tick drops anything at time "zero"

    def process_instructions(self, stall):
        instructions = self.stages[0] # get list of instructions
        to_write = set()              # need to know total writes
        for instruction in instructions:
            to_write.update(instruction['writes'])
        # see if all writes can be done, otherwise stall
        writes_possible = self.cpu.writes_possible(to_write)
        if writes_possible != to_write:
            stall = True
        # retire the writes that are possible in this cycle (regfile writes)
        self.cpu.regs.retire_write(writes_possible)
        # and now go through the instructions, removing those regs written
        for instruction in instructions:
            instruction['writes'].difference_update(writes_possible)
        return stall


class Fetch:
    """
    Fetch: reads the next log-entry and puts it into the queue.
    """
    def __init__(self, cpu):
        self.stages = [None] # only ever going to be 1 long but hey
        self.cpu = cpu

    def tick(self):
        self.stages[0] = None

    def process_instructions(self, stall):
        if stall: return stall
        insn = self.stages[0] # get current instruction
        if insn is not None:
            self.cpu.decode.add_instructions(insn) # pass on instruction
        # read from log file, write into self.stages[0]
        # XXX TODO
        return stall


class Decode:
    """
    Decode: performs a "decode" of the instruction. identifies and records
    read/write regs. the reads/writes possible should likely not all be here,
    perhaps split across "Issue"?
    """
    def __init__(self, cpu):
        self.stages = [None] # only ever going to be 1 long but hey
        self.cpu = cpu

    def add_instruction(self, insn):
        # get the read and write regs
        writeregs = get_input_regs(insn)
        readregs = get_output_regs(insn)
        assert self.stages[0] is None # must be empty (tick or stall)
        self.stages[0] = (insn, writeregs, readregs)

    def tick(self):
        self.stages[0] = None

    def process_instructions(self, stall):
        if stall: return stall
        # get current instruction
        insn, writeregs, readregs = self.stages[0]
        # check that the readregs are all available
        reads_possible = self.cpu.reads_possible(readregs)
        stall = reads_possible != readregs
        # perform the "reads" that are possible in this cycle
        readregs.difference_update(reads_possible)
        # and "Reserves" the writes
        self.cpu.expect_write(writeregs)
        # now pass the instruction on to Issue
        self.cpu.issue.add_instruction(insn, writeregs)
        return stall


class Issue:
    """
    Issue phase: if not stalled will place the instruction into execute.
    TODO: move the reading and writing of regs here.
    """
    def __init__(self, cpu):
        self.stages = [None] # only ever going to be 1 long but hey
        self.cpu = cpu

    def add_instruction(self, insn, writeregs):
        # get the read and write regs
        assert self.stages[0] is None # must be empty (tick or stall)
        self.stages[0] = (insn, writeregs)

    def tick(self):
        self.stages[0] = None

    def process_instructions(self, stall):
        if stall: return stall
        self.cpu.execute.add_instructions(self.stages[0])
        return stall


class CPU:
    """
    CPU: contains Fetch, Decode, Issue and Execute pipelines, and regs.
    Reads "instructions" from a file, starts putting them into a pipeline,
    and monitors hazards.  first version looks only for register hazards.
    """
    def __init__(self):
        self.regs = RegisterWrite()
        self.fetch = Fetch(self)
        self.decode = Decode(self)
        self.issue = Issue(self)
        self.exe = Execute(self)
        self.stall = False

    def reads_possible(self, regs):
        # TODO: subdivide this down by GPR FPR CR-field.
        # currently assumes total of 3 regs are readable at one time
        possible = set()
        r = regs.copy()
        while len(possible) < 3 and len(r) > 0:
            possible.add(r.pop())
        return possible

    def writess_possible(self, regs):
        # TODO: subdivide this down by GPR FPR CR-field.
        # currently assumes total of 1 reg is possible regardless of what it is
        possible = set()
        r = regs.copy()
        while len(possible) < 1 and len(r) > 0:
            possible.add(r.pop())
        return possible

    def process_instructions(self):
        stall = self.stall
        stall = self.fetch.process_instructions(stall)
        stall = self.decode.process_instructions(stall)
        stall = self.issue.process_instructions(stall)
        stall = self.exe.process_instructions(stall)
        self.stall = stall
        if not stall:
            self.fetch.tick()
            self.decode.tick()
            self.issue.tick()
            self.exe.tick()

class TestTrace(unittest.TestCase):

    def test_trace(self): # TODO, assert this is valid
        lines = (
            "r:GPR:0:0:64 w:GPR:1:0:64 # addi 1, 0, 0x0010",
            "r:GPR:0:0:64 w:GPR:2:0:64 # addi 2, 0, 0x1234",
            "r:GPR:1:0:64 r:GPR:2:0:64 # stw 2, 0(1)",
            "r:GPR:1:0:64 w:GPR:3:0:64 # lwz 3, 0(1)",
            "r:GPR:3:0:64 r:GPR:2:0:64 w:GPR:1:0:64 # add 1, 3, 2",
            "r:GPR:0:0:64 w:GPR:3:0:64 # addi 3, 0, 0x1234",
            "r:GPR:0:0:64 w:GPR:2:0:64 # addi 2, 0, 0x4321",
            "r:GPR:3:0:64 r:GPR:2:0:64 w:GPR:1:0:64 # add  1, 3, 2",
        )
        f = io.StringIO("\n".join(lines))
        lines = read_file(f)
        for trace in lines:
            print(trace)


if __name__ == "__main__":
    unittest.main()

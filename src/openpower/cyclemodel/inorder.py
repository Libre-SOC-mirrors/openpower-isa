#!/usr/bin/env python3
# Copyright (C) 2023 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Copyright (C) 2023 Dimitry Selyutin <ghostmansd@gmail.com>
# LGPLv3+
# Funded by NLnet
#
# An In-order cycle-accurate model of a Power ISA 3.0 hardware implementation
#
#       This program should be entirely self-sufficient such that it may be
#       published in a magazine, or in a specification, or on another website,
#       or as part of an Academic Paper (please ensure Attribution/Copyright
#       is retained: distribution without these Copyright Notices intact is
#       prohibited).
#
#       It should therefore not import complex modules (regex, dataclass)
#       keeping to simple techniques and simple python modules that are
#       easy to understand.  readability comments are crucial.  Unit tests
#       should be bare-minimum practical demonstrations but also within this
#       file, and additional unit tests in separate files (listed below)
#
#       Duplication of code from other models in this series is perfectly
#       acceptable in order to respect the self-sufficiency requirement.
#
# Bugs:
#
# * https://bugs.libre-soc.org/show_bug.cgi?id=1039
#
# Separate Unit tests:
#
# * TODO
#
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
import getopt
import sys

# trace file entries are lists of these.
Hazard = namedtuple("Hazard", ["action", "target", "ident", "offs", "elwid"])

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
    """reads a trace file in the form "[{rw}:FILE:regnum:offset:width]* # insn"
    this function is a generator, it yields a list comprising each line:
    ["insn", Hazard(...), Hazard(....), ....]

    fname may be a *file* (an object) with a function named "read",
    in which case the Contract is that it is the *CALLER* that must
    take responsibility for the file: opening, closing, seeking.

    if fname is a string then this function will take care of reading
    from it and is itself responsible for closing the file handle.
    """
    is_file = hasattr(fname, "read")
    if not is_file:
        fname = open(fname, "r")

    for line in fname.readlines():
        (specs, insn) = map(str.strip, line.strip().split("#"))
        line = [insn]
        for spec in specs.split(" "):
            line.append(Hazard._make(spec.split(":")))
        yield line
    if not is_file:
        fname.close()

def get_input_regs(hazards):
    input_regs = set()
    for hazard in hazards:
        if hazard.action == 'r':
            # return the reg to be read
            input_regs.update([(hazard.target, hazard.ident)])
    return input_regs

def get_output_regs(hazards):
    output_regs = set()
    for hazard in hazards:
        if hazard.action == 'w':
            # return the reg to be read
            output_regs.update([(hazard.target, hazard.ident)])
    return output_regs


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
        # if add_instruction cycle_away=2 means there are three entries,
        # [0], [1], [2], need to append one more entry.
        while cycles_away > len(self.stages) - 1:
            self.stages.append([])
        self.stages[cycles_away].append(stage)

    def add_instruction(self, insn, writeregs):
        self.add_stage(2, {'insn': insn, 'writes': writeregs})

    def tick(self):
        if len(self.stages) > 0:
            self.stages.pop(0) # tick drops anything at time "zero"

    def process_instructions(self, stall):
        if len(self.stages) == 0: return stall

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
        # Flag which indicates if fetch should be pushing insn to decode,
        # else there won't be an initial one-clock delay between fetch and dec
        self.pushed_to_decode = False

    def tick(self):
        # only clear stage if the instruction has actually been pushed to decode
        if self.pushed_to_decode:
            self.stages[0] = None

    def process_instructions(self, stall, insn_trace):
        if stall:
            return stall
        insn = self.stages[0] # get current instruction
        if insn is not None:
            self.cpu.decode.add_instruction(insn) # pass on instruction
        # read from log file, write into self.stages[0]
        self.stages[0] = insn_trace
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

    def add_instruction(self, insn_trace):
        # get the read and write regs
        insn = insn_trace[0]
        readregs = get_input_regs(insn_trace[1:])
        writeregs = get_output_regs(insn_trace[1:])
        assert self.stages[0] is None # must be empty (tick or stall)
        self.stages[0] = (insn, writeregs, readregs)

    def tick(self):
        self.stages[0] = None

    def process_instructions(self, stall):
        if stall:
            return stall

        if self.stages[0] is None: return stall

        # get current instruction
        insn, writeregs, readregs = self.stages[0]
        # check that the readregs are all available
        reads_possible = self.cpu.reads_possible(readregs)
        stall = reads_possible != readregs
        # perform the "reads" that are possible in this cycle
        readregs.difference_update(reads_possible)
        # and "Reserves" the writes
        self.cpu.regs.expect_write(writeregs)
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
        if stall:
            return stall

        if self.stages[0] is None: return stall

        insn, writeregs = self.stages[0]
        self.cpu.exe.add_instruction(insn, writeregs)
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
        self.curr_clk = 0

    def reads_possible(self, regs):
        # TODO: subdivide this down by GPR FPR CR-field.
        # currently assumes total of 3 regs are readable at one time
        possible = set()
        r = regs.copy()
        while len(possible) < 3 and len(r) > 0:
            possible.add(r.pop())
        return possible

    def writes_possible(self, regs):
        # TODO: subdivide this down by GPR FPR CR-field.
        # currently assumes total of 1 reg is possible regardless of what it is
        possible = set()
        r = regs.copy()
        while len(possible) < 1 and len(r) > 0:
            possible.add(r.pop())
        return possible

    # Inverting the stage order ensures that instructions already in the
    # pipeline get processed first.
    def process_instructions(self, insn_trace):
        #print("Start of CPU cycle, clk=%d" % self.curr_clk)
        stall = self.stall
        stall = self.exe.process_instructions(stall)
        stall = self.issue.process_instructions(stall)
        stall = self.decode.process_instructions(stall)
        stall = self.fetch.process_instructions(stall, insn_trace)
        self.stall = stall
        self.print_cur_state()
        if not stall:
            self.fetch.tick()
            self.decode.tick()
            self.issue.tick()
            self.exe.tick()
        self.curr_clk += 1
        #print("---------------")

    # TODO: Make formatting prettier, and conform to markdown table format
    # TODO: Adjust based on actual number of pipeline stages.
    def print_headings(self):
        print("| clk # | fetch | decode | issue | exec |")

    def print_cur_state(self):
        string = "| %d | " % self.curr_clk
        if self.stall:
            string += " STALL "
        else:
            if self.fetch.stages[0] is not None:
                string += self.fetch.stages[0][0]
            else:
                string += "     "
        string += "| "
        if self.decode.stages[0] is not None:
            string += self.decode.stages[0][0]
        else:
            string += "      "
        string += "| "
        if self.issue.stages[0] is not None:
            string += self.issue.stages[0][0]
        else:
            string += "     "
        string += "| "
        if len(self.exe.stages) > 0 and len(self.exe.stages[0]) > 0:
            #print("Execute stages: ", self.exe.stages)
            #print(type(self.exe.stages[0]), self.exe.stages[0])
            string += self.exe.stages[0][0]['insn']
        else:
            string += "    "
        string += "|"
        print(string)

class TestTrace(unittest.TestCase):

    def test_trace(self): # TODO, assert this is valid
        basic_cpu = CPU()

        lines = (
            "r:GPR:0:0:64 w:GPR:1:0:64              # addi 1, 0, 0x0010",
            "r:GPR:0:0:64 w:GPR:2:0:64              # addi 2, 0, 0x1234",
            "r:GPR:1:0:64 r:GPR:2:0:64              # stw 2, 0(1)",
            "r:GPR:1:0:64 w:GPR:3:0:64              # lwz 3, 0(1)",
            "r:GPR:3:0:64 r:GPR:2:0:64 w:GPR:1:0:64 # add 1, 3, 2",
            "r:GPR:0:0:64 w:GPR:3:0:64              # addi 3, 0, 0x1234",
            "r:GPR:0:0:64 w:GPR:2:0:64              # addi 2, 0, 0x4321",
            "r:GPR:3:0:64 r:GPR:2:0:64 w:GPR:1:0:64 # add  1, 3, 2",
        )
        f = io.StringIO("\n".join(lines))
        lines = read_file(f)
        basic_cpu.print_headings()
        for trace in lines:
            #print(trace)
            basic_cpu.process_instructions(trace)

    def test_trace1(self): # TODO, assert this is valid
        basic_cpu = CPU()

        lines = (
            "r:GPR:0:0:64 w:GPR:1:0:64              # addi 1, 0, 0x0010",
            "r:GPR:1:0:64 w:GPR:2:0:64              # addi 2, 1, 0x1234",
        )
        f = io.StringIO("\n".join(lines))
        lines = read_file(f)
        basic_cpu.print_headings()
        for trace in lines:
            #print(trace)
            basic_cpu.process_instructions(trace)

def help():
    print ("-t             runs unit tests")
    print ("-h --help      prints this message")
    exit(-1)


if __name__ == "__main__":
    opts, args = getopt.getopt(sys.argv[1:], "thi:o:",
                                             ["help",])

    # default files are stdin/stdout.
    in_file = sys.stdin
    out_file = sys.stdout

    for opt, arg in opts:
        if opt in ['-h', '--help']:
            help()
        if opt in ['-t']:
            unittest.main(argv=[sys.argv[0]]+sys.argv[2:])
        if opt in ['-i']:
            in_file = arg
        if opt in ['-o']:
            out_file = arg

    # TODO: run model
    lines = read_file(in_file)
    for trace in lines:
        out_file.write("|" + "|".join(map(str, trace)) + "|\n")

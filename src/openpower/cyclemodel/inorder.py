#!/usr/bin/env python3
# An In-order cycle-accurate model of a Power ISA 3.0 hardware implementation
# LGPLv3+
# Funded by NLnet
#
# Bugs: https://bugs.libre-soc.org/show_bug.cgi?id=1039

class RegisterWrite(set):
    """RegisterWrite: contains the set of Read-after-Write Hazards.
    Anything in this set must be a STALL at Decode phase because the
    answer has still not popped out the end of a pipeline
    """
    def expect_write(self, regs): self.update(regs)
    def write_expected(self, regs): len(self.intersection(regs)) != 0
    def retire_write(self, regs): self.difference_update(regs)

class Execute:
    """Execute Pipeline: keeps a countdown-sorted list of instructions
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

    def process_instructions(self):
        stall = False                 # stalls if not all writes possible
        instructions = self.stages[0] # get list of instructions
        to_write = set()              # need to know total writes
        for instruction in instructions:
            to_write.update(instruction['writes'])
        # see if all writes can be done, otherwise stall
        writes_possible = self.cpu.all_writes_possible(to_write):
        if writes_possible != to_write:
            stall = True
        # retire the writes that are possible in this cycle (regfile writes)
        self.cpu.regs.retire_write(writes_possible)
        # and now go through the instructions, removing those regs written
        for instruction in instructions:
            instruction['writes'].difference_update(writes_possible)
        return stall

class Decode:
    def __init__(self, cpu):
        self.stages = [] # only ever going to be 1 long but hey
        self.cpu = cpu

    def add_instruction(self, insn):
        # get the read and write regs
        writeregs = get_input_regs(insn)
        readregs = get_output_regs(insn)


class CPU:
    """CPU: contains Fetch, Decode, Issue and Execute pipelines, and regs.
    Reads "instructions" from a file, starts putting them into a pipeline,
    and monitors hazards.  first version looks only for register hazards.
    """
    def __init__(self):
        self.regs = RegisterWrite()
        self.fetch = Fetch(self)
        self.decode = Decode(self)
        self.issue = Issue(self)
        self.exe = Execute(self)

    def process_instructions(self):
        stall = self.fetch.process_instructions()
        stall |= self.decode.process_instructions()
        stall |= self.issue.process_instructions()
        stall |= self.exe.process_instructions()
        if not stall:
            self.fetch.tick()
            self.decode.tick()
            self.issue.tick()
            self.exe.tick()


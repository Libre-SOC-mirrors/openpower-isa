#!/usr/bin/env python3
# An In-order cycle-accurate model of a Power ISA 3.0 hardware implementation

class RegisterWrite(set):
    def expect_write(self, regs): self.update(regs)
    def write_expected(self, regs): len(self.intersection(regs)) != 0
    def retire_write(self, regs): self.difference_update(regs)

class Execute:
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
        self.stages.pop(0)

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
        self.cpu.regs.retire_write(to_write)
        return stall

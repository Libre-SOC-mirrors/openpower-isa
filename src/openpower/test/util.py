# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2023 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

import re
from openpower.insndb.asm import SVP64Asm
from openpower.simulator.program import Program
from functools import lru_cache


def assemble(instructions, start_pc=0, bigendian=False):
    """ assemble `instructions`, handling labels.
        returns a Program instance
    """
    return __cached_assemble(tuple(instructions), start_pc, bigendian)


@lru_cache(maxsize=10000)
def __cached_assemble(instructions, start_pc, bigendian):
    pc = start_pc
    labels = {}
    out_instructions = []
    for instr in instructions:
        m = re.fullmatch(r" *([a-zA-Z0-9_.$]+): *(#.*)?", instr)
        if m is not None:
            name = m.group(1)
            if name in labels:
                raise ValueError(f"label {name!r} defined multiple times")
            labels[name] = pc
            continue
        m = re.fullmatch(r" *sv\.[a-zA-Z0-9_].*", instr)
        if m is not None:
            pc += 8
        else:
            pc += 4
        out_instructions.append((pc, instr))
    last_pc = pc

    for (idx, (pc, instr)) in enumerate(tuple(out_instructions)):
        need_replace = True

        def replace(match):
            nonlocal need_replace
            label = match.group(1)
            target = labels.get(label)
            if target is not None:
                need_replace = True
                if pc < target:
                    sign = ""
                    addr = (target - pc + 4)
                else:
                    sign = "-"
                    addr = (pc - target - 4)
                return f"{sign}0x{addr:X}"
            return label

        while need_replace:
            need_replace = False
            # gas symbols start with any alphabetic or _ . $
            start = "[a-zA-Z_.$]"
            # gas symbols continue with any alphanumeric or _ . $
            cont = "[a-zA-Z0-9_.$]"
            # look for symbols that don't have preceding/succeeding `cont`
            instr = re.sub(f"({start}{cont}*)", replace, instr)
        out_instructions[idx] = instr

    for k, v in labels.items():
        out_instructions.append(f".set {k}, . - 0x{last_pc - v:X} # 0x{v:X}")

    return Program(list(SVP64Asm(out_instructions)), bigendian)

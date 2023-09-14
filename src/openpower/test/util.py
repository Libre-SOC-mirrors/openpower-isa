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
        m = re.fullmatch(r" *([a-zA-Z0-9_]+): *(#.*)?", instr)
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
        for (label, target) in labels.items():
            if label in instr:
                if pc < target:
                    sign = ""
                    addr = (target - pc + 4)
                else:
                    sign = "-"
                    addr = (pc - target - 4)

                origin = instr
                instr = instr.replace(label, f"{sign}0x{addr:X}")
                break
        out_instructions[idx] = instr

    for k, v in labels.items():
        out_instructions.append(f".set {k}, . - 0x{last_pc - v:X} # 0x{v:X}")

    return Program(list(SVP64Asm(out_instructions)), bigendian)

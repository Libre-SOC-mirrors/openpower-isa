# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

""" Tree-based Reduction as a Python Generator.

https://bugs.libre-soc.org/show_bug.cgi?id=697
"""

from openpower.util.text_tree_graph import Op, print_tree


class Move(Op):
    def __init__(self, out, in_):
        super().__init__((out,), (in_,))


class FAdd(Op):
    def __init__(self, out, in0, in1):
        super().__init__((out,), (in0, in1))


def tree_reduce(bitmask, vl, remap=None, bin_op=FAdd):
    assert isinstance(vl, int) and vl >= 0
    assert isinstance(bitmask, int)
    arg_dist = 1
    while arg_dist < vl:
        for i0 in range(0, vl, arg_dist * 2):
            i1 = i0 + arg_dist
            if remap is not None:
                # FIXME(lkcl): does remap remap bitmask indexes like it does
                # register indexes? This code assumes so.
                i0 = remap[i0]
                i1 = remap[i1]
            if (bitmask >> i1) & 1:
                if (bitmask >> i0) & 1:
                    yield bin_op(i0, i0, i1)
                else:
                    yield Move(i0, i1)
                bitmask |= 1 << i0
        arg_dist *= 2


if __name__ == "__main__":
    for vl in range(0, 6):
        for bitmask in range(2 ** vl):
            print(f"vl={vl} bitmask={bin(bitmask)[2:].zfill(vl)}:")
            program = list(tree_reduce(bitmask, vl))
            for op in program:
                print(f"    {op!s}")
            # TODO: re-enable:
            # print_tree(program)

# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2020, 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Funded by NLnet http://nlnet.nl
"""core of the python-based POWER9 simulator

this is part of a cycle-accurate POWER9 simulator.  its primary purpose is
not speed, it is for both learning and educational purposes, as well as
a method of verifying the HDL.

related bugs:

* https://bugs.libre-soc.org/show_bug.cgi?id=424
"""

from collections import defaultdict
from openpower.decoder.selectable_int import SelectableInt
from openpower.util import log, LogKind
import math


def swap_order(x, nbytes):
    x = x.to_bytes(nbytes, byteorder='little')
    x = int.from_bytes(x, byteorder='big', signed=False)
    return x


class MemException(Exception):
    pass

def process_mem(initial_mem, row_bytes=8):
    res = {}
    # different types of memory data structures recognised (for convenience)
    if isinstance(initial_mem, list):
        initial_mem = (0, initial_mem)
    if isinstance(initial_mem, tuple):
        startaddr, mem = initial_mem
        initial_mem = {}
        for i, val in enumerate(mem):
            initial_mem[startaddr + row_bytes*i] = (val, row_bytes)

    for addr, val in initial_mem.items():
        if isinstance(val, tuple):
            (val, width) = val
        else:
            width = row_bytes # assume same width
        #val = swap_order(val, width)
        res[addr] = (val, width)

    return res


class Mem:

    def __init__(self, row_bytes=8, initial_mem=None, misaligned_ok=False):
        self.mem = {}
        self.bytes_per_word = row_bytes
        self.word_log2 = math.ceil(math.log2(row_bytes))
        self.last_ld_addr = None
        self.last_st_addr = None
        self.misaligned_ok = misaligned_ok
        log("Sim-Mem", initial_mem, self.bytes_per_word, self.word_log2)
        if not initial_mem:
            return

        for addr, (val, width) in process_mem(initial_mem, row_bytes).items():
            #val = swap_order(val, width)
            self.st(addr, val, width, swap=False)

    def _get_shifter_mask(self, wid, remainder):
        shifter = ((self.bytes_per_word - wid) - remainder) * \
            8  # bits per byte
        # XXX https://bugs.libre-soc.org/show_bug.cgi?id=377
        # BE/LE mode?
        shifter = remainder * 8
        mask = (1 << (wid * 8)) - 1
        log("width,rem,shift,mask", wid, remainder, hex(shifter), hex(mask))
        return shifter, mask

    # TODO: Implement ld/st of lesser width
    def ld(self, address, width=8, swap=True, check_in_mem=False,
                 instr_fetch=False):
        log("ld from addr 0x%x width %d" % (address, width),
                swap, check_in_mem, instr_fetch)
        self.last_ld_addr = address # record last load
        ldaddr = address
        remainder = address & (self.bytes_per_word - 1)
        address = address >> self.word_log2
        if remainder & (width - 1) != 0:
            exc = MemException("unaligned",
                  "Unaligned access: remainder %x width %d" % \
                  (remainder, width))
            exc.dar = ldaddr
            raise exc
        if address in self.mem:
            val = self.mem[address]
        elif check_in_mem:
            return None
        else:
            val = 0
        log("ld mem @ 0x%x rem %d : 0x%x" % (ldaddr, remainder, val))

        if width != self.bytes_per_word:
            shifter, mask = self._get_shifter_mask(width, remainder)
            log("masking", hex(val), hex(mask << shifter), shifter)
            val = val & (mask << shifter)
            val >>= shifter
        if swap:
            val = swap_order(val, width)
        log("Read 0x%x from addr 0x%x" % (val, ldaddr))
        return val

    def _st(self, addr, v, width=8, swap=True):
        staddr = addr
        remainder = addr & (self.bytes_per_word - 1)
        addr = addr >> self.word_log2
        log("Writing 0x%x to ST 0x%x memaddr 0x%x/%x swap %s" % \
            (v, staddr, addr, remainder, str(swap)))
        if remainder & (width - 1) != 0:
            exc = MemException("unaligned",
                  "Unaligned access: remainder %x width %d" % \
                  (remainder, width))
            exc.dar = staddr
            raise exc
        if swap:
            v = swap_order(v, width)
        if width != self.bytes_per_word:
            if addr in self.mem:
                val = self.mem[addr]
            else:
                val = 0
            shifter, mask = self._get_shifter_mask(width, remainder)
            val &= ~(mask << shifter)
            val |= v << shifter
            self.mem[addr] = val
        else:
            self.mem[addr] = v
        log("mem @ 0x%x: 0x%x" % (staddr, self.mem[addr]))

    def st(self, addr, v, width=8, swap=True):
        staddr = addr
        self.last_st_addr = addr # record last store
        # misaligned not allowed: pass straight to Mem._st
        if not self.misaligned_ok:
            return self._st(addr, v, width, swap)
        remainder = addr & (self.bytes_per_word - 1)
        addr = addr >> self.word_log2
        if swap:
            v = swap_order(v, width)
        # not misaligned: pass through to Mem._st but we've swapped already
        if remainder & (width - 1) == 0:
            return self._st(addr, v, width, swap=False)
        shifter, mask = self._get_shifter_mask(width, remainder)
        print ("mask", hex(shifter), hex(mask))

    def __call__(self, addr, sz):
        val = self.ld(addr.value, sz, swap=False)
        log("memread", addr, sz, val)
        return SelectableInt(val, sz*8)

    def memassign(self, addr, sz, val):
        log("memassign", addr, sz, val)
        self.st(addr.value, val.value, sz, swap=False)

    def dump(self, printout=True, asciidump=False):
        keys = list(self.mem.keys())
        keys.sort()
        res = []
        for k in keys:
            res.append(((k*8), self.mem[k]))
            if not printout:
                continue
            s = ""
            if asciidump:
                for i in range(8):
                    c = chr(self.mem[k]>>(i*8) & 0xff)
                    if not c.isprintable():
                        c = "."
                    s += c
            print ("%016x: %016x" % ((k*8) & 0xffffffffffffffff,
                                     self.mem[k]), s)
        return res

    def log_fancy(self, *, kind=LogKind.Default, name="Memory",
                  log2_line_size=4, log2_column_chunk_size=3, log=log):
        line_size = 1 << log2_line_size
        subline_mask = line_size - 1
        column_chunk_size = 1 << log2_column_chunk_size

        def make_line():
            return bytearray(line_size)
        mem_lines = defaultdict(make_line)
        subword_range = range(1 << self.word_log2)
        for k in self.mem.keys():
            addr = k << self.word_log2
            for _ in subword_range:
                v = self.ld(addr, width=1)
                mem_lines[addr >> log2_line_size][addr & subline_mask] = v
                addr += 1

        lines = []
        last_line_index = None
        for line_index in sorted(mem_lines.keys()):
            line_addr = line_index << log2_line_size
            if last_line_index is not None \
                    and last_line_index + 1 != line_index:
                lines.append("*")
            last_line_index = line_index
            line_bytes = mem_lines[line_index]
            line_str = f"0x{line_addr:08X}:"
            for col_chunk in range(0, line_size,
                                   column_chunk_size):
                line_str += " "
                for i in range(column_chunk_size):
                    line_str += f" {line_bytes[col_chunk + i]:02X}"
            line_str += "  |"
            for i in range(line_size):
                if 0x20 <= line_bytes[i] <= 0x7E:
                    line_str += chr(line_bytes[i])
                else:
                    line_str += "."
            line_str += "|"
            lines.append(line_str)
        lines = "\n".join(lines)
        log(f"\n{name}:\n{lines}\n", kind=kind)

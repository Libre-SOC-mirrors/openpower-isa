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
import enum
from cached_property import cached_property
import mmap
from pickle import PicklingError
import ctypes


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
            width = row_bytes  # assume same width
        # val = swap_order(val, width)
        res[addr] = (val, width)

    return res


@enum.unique
class _ReadReason(enum.Enum):
    Read = enum.auto()
    SubWordWrite = enum.auto()
    Dump = enum.auto()
    Execute = enum.auto()

    @cached_property
    def read_default(self):
        if self in (self.SubWordWrite, self.Dump):
            return 0
        return None

    @cached_property
    def needed_mmap_page_flag(self):
        if self is self.Execute:
            return _MMapPageFlags.X
        return _MMapPageFlags.R


class MemCommon:
    def __init__(self, row_bytes, initial_mem, misaligned_ok):
        self.bytes_per_word = row_bytes
        self.word_log2 = math.ceil(math.log2(row_bytes))
        self.last_ld_addr = None
        self.last_st_addr = None
        self.misaligned_ok = misaligned_ok
        log("Sim-Mem", initial_mem, self.bytes_per_word, self.word_log2)
        if not initial_mem:
            return

        self.initialize(row_bytes, initial_mem)

    def initialize(self, row_bytes, initial_mem):
        for addr, (val, width) in process_mem(initial_mem, row_bytes).items():
            # val = swap_order(val, width)
            self.st(addr, val, width, swap=False)

    def _read_word(self, word_idx, reason):
        raise NotImplementedError

    def _write_word(self, word_idx, value):
        raise NotImplementedError

    def word_idxs(self):
        raise NotImplementedError
        yield 0

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
           instr_fetch=False, reason=None):
        log("ld from addr 0x%x width %d" % (address, width),
            swap, check_in_mem, instr_fetch)
        self.last_ld_addr = address  # record last load
        ldaddr = address
        remainder = address & (self.bytes_per_word - 1)
        address = address >> self.word_log2
        if remainder & (width - 1) != 0:
            exc = MemException("unaligned",
                               "Unaligned access: remainder %x width %d" %
                               (remainder, width))
            exc.dar = ldaddr
            raise exc
        if reason is None:
            reason = _ReadReason.Execute if instr_fetch else _ReadReason.Read
        val = self._read_word(address, reason)
        if val is None:
            if check_in_mem:
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
        log("Writing 0x%x to ST 0x%x memaddr 0x%x/%x swap %s" %
            (v, staddr, addr, remainder, str(swap)))
        if not self.misaligned_ok and remainder & (width - 1) != 0:
            exc = MemException("unaligned",
                               "Unaligned access: remainder %x width %d" %
                               (remainder, width))
            exc.dar = staddr
            raise exc
        if swap:
            v = swap_order(v, width)
        if width != self.bytes_per_word:
            val = self._read_word(addr, _ReadReason.SubWordWrite)
            shifter, mask = self._get_shifter_mask(width, remainder)
            val &= ~(mask << shifter)
            val |= v << shifter
            self._write_word(addr, val)
        else:
            val = v
            self._write_word(addr, v)
        log("mem @ 0x%x: 0x%x" % (staddr, val))

    def st(self, st_addr, v, width=8, swap=True):
        self.last_st_addr = st_addr  # record last store
        # misaligned not allowed: pass straight to Mem._st
        if not self.misaligned_ok:
            return self._st(st_addr, v, width, swap)
        remainder = st_addr & (self.bytes_per_word - 1)
        if swap:
            v = swap_order(v, width)
        # not misaligned: pass through to Mem._st but we've swapped already
        misaligned = remainder & (width - 1)
        if misaligned == 0 or (remainder + width <= self.bytes_per_word):
            return self._st(st_addr, v, width, swap=False)
        shifter, mask = self._get_shifter_mask(width, remainder)
        # split into two halves. lower first
        maxmask = (1 << (self.bytes_per_word)*8) - 1
        val1 = ((v << shifter) & maxmask) >> shifter
        self._st(st_addr, val1, width=width-misaligned, swap=False)
        # now upper.
        val2 = v >> ((width-misaligned)*8)
        addr2 = (st_addr >> self.word_log2) << self.word_log2
        addr2 += self.bytes_per_word
        print("v, val2", hex(v), hex(val2), "ad", addr2)
        self._st(addr2, val2, width=width-misaligned, swap=False)

    def __call__(self, addr, sz):
        val = self.ld(addr.value, sz, swap=False)
        log("memread", addr, sz, val)
        return SelectableInt(val, sz*8)

    def memassign(self, addr, sz, val):
        log("memassign", addr, sz, val)
        self.st(addr.value, val.value, sz, swap=False)

    def dump(self, printout=True, asciidump=False):
        keys = list(self.word_idxs())
        keys.sort()
        res = []
        for k in keys:
            v = self._read_word(k, _ReadReason.Dump)
            res.append((k*8, v))
            if not printout:
                continue
            s = ""
            if asciidump:
                for i in range(8):
                    c = chr(v >> (i*8) & 0xff)
                    if not c.isprintable():
                        c = "."
                    s += c
            print("%016x: %016x" % ((k*8) & 0xffffffffffffffff, v), s)
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
        for k in self.word_idxs():
            addr = k << self.word_log2
            for _ in subword_range:
                v = self.ld(addr, width=1, reason=_ReadReason.Dump)
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


class Mem(MemCommon):
    def __init__(self, row_bytes=8, initial_mem=None, misaligned_ok=False):
        self.mem = {}
        super().__init__(row_bytes, initial_mem, misaligned_ok)

    def _read_word(self, word_idx, reason):
        return self.mem.get(word_idx, reason.read_default)

    def _write_word(self, word_idx, value):
        self.mem[word_idx] = value

    def word_idxs(self):
        return self.mem.keys()


class _MMapPageFlags(enum.IntFlag):
    """ flags on each mmap-ped page

    Note: these are *not* PowerISA MMU pages, but instead internal to Mem so
    it can detect invalid accesses and assert rather than segfaulting.
    """
    R = 1
    W = 2
    X = 4
    "readable when instr_fetch=True"

    RWX = R | W | X


_MMAP_PAGE_SIZE = 1 << 16  # size of chunk that we track
_PAGE_COUNT = (1 << 48) // _MMAP_PAGE_SIZE  # 48-bit address space
_NEG_PG_IDX_START = _PAGE_COUNT // 2  # start of negative half of address space
BLOCK_SIZE = 1 << 32  # code assumes it's a power of two
assert BLOCK_SIZE % _MMAP_PAGE_SIZE == 0
DEFAULT_BLOCK_ADDRS = (
    0,  # low end of user space
    2 ** 47 - BLOCK_SIZE,  # high end of user space
)


class MemMMap(MemCommon):
    def __init__(self, row_bytes=8, initial_mem=None, misaligned_ok=False,
                 block_addrs=DEFAULT_BLOCK_ADDRS, emulating_mmap=False):
        # we can't allocate the entire 2 ** 47 byte address space, so split
        # it into smaller blocks
        self.mem_blocks = {
            addr: mmap.mmap(-1, BLOCK_SIZE) for addr in block_addrs}
        assert all(addr % BLOCK_SIZE == 0 for addr in self.mem_blocks), \
            "misaligned block address not supported"
        self.page_flags = {}
        self.modified_pages = set()
        if not emulating_mmap:
            # mark blocks as readable/writable
            for addr, block in self.mem_blocks.items():
                start_page_idx = addr // _MMAP_PAGE_SIZE
                end_page_idx = start_page_idx + len(block) // _MMAP_PAGE_SIZE
                for page_idx in range(start_page_idx, end_page_idx):
                    self.page_flags[page_idx] = _MMapPageFlags.RWX

        super().__init__(row_bytes, initial_mem, misaligned_ok)

    def mmap_page_idx_to_addr(self, page_idx):
        assert 0 <= page_idx < _PAGE_COUNT
        if page_idx >= _NEG_PG_IDX_START:
            page_idx -= _PAGE_COUNT
        return (page_idx * _MMAP_PAGE_SIZE) % 2 ** 64

    def addr_to_mmap_page_idx(self, addr):
        page_idx, offset = divmod(addr, _MMAP_PAGE_SIZE)
        page_idx %= _PAGE_COUNT
        expected = self.mmap_page_idx_to_addr(page_idx) + offset
        if addr != expected:
            exc = MemException("not sign extended",
                               f"address not sign extended: 0x{addr:X} "
                               f"expected 0x{expected:X}")
            exc.dar = addr
            raise exc
        return page_idx

    def __reduce_ex__(self, protocol):
        raise PicklingError("MemMMap can't be deep-copied or pickled")

    def __access_addr_range_err(self, start_addr, size, needed_flag):
        assert needed_flag != _MMapPageFlags.W, \
            f"can't write to address 0x{start_addr:X} size 0x{size:X}"
        return None, 0

    def __access_addr_range(self, start_addr, size, needed_flag):
        assert size > 0, "invalid size"
        page_idx = self.addr_to_mmap_page_idx(start_addr)
        last_addr = start_addr + size - 1
        last_page_idx = self.addr_to_mmap_page_idx(last_addr)
        block_addr = start_addr % BLOCK_SIZE
        block_k = start_addr - block_addr
        last_block_addr = last_addr % BLOCK_SIZE
        last_block_k = last_addr - last_block_addr
        if block_k != last_block_k:
            return self.__access_addr_range_err(start_addr, size, needed_flag)
        for i in range(page_idx, last_page_idx + 1):
            flags = self.page_flags.get(i, 0)
            if flags & needed_flag == 0:
                return self.__access_addr_range_err(
                    start_addr, size, needed_flag)
            if needed_flag is _MMapPageFlags.W:
                self.modified_pages.add(page_idx)
        return self.mem_blocks[block_k], block_addr

    def get_ctypes(self, start_addr, size, is_write):
        """ returns a ctypes ubyte array referring to the memory at
        `start_addr` with size `size`
        """
        flag = _MMapPageFlags.W if is_write else _MMapPageFlags.R
        block, block_addr = self.__access_addr_range(start_addr, size, flag)
        assert block is not None, \
            f"can't read from address 0x{start_addr:X} size 0x{size:X}"
        return (ctypes.c_ubyte * size).from_buffer(block, block_addr)

    def _read_word(self, word_idx, reason):
        block, block_addr = self.__access_addr_range(
            word_idx * self.bytes_per_word, self.bytes_per_word,
            reason.needed_mmap_page_flag)
        if block is None:
            return reason.read_default
        bytes_ = block[block_addr:block_addr + self.bytes_per_word]
        return int.from_bytes(bytes_, 'little')

    def _write_word(self, word_idx, value):
        block, block_addr = self.__access_addr_range(
            word_idx * self.bytes_per_word, self.bytes_per_word,
            _MMapPageFlags.W)
        bytes_ = value.to_bytes(self.bytes_per_word, 'little')
        block[block_addr:block_addr + self.bytes_per_word] = bytes_

    def word_idxs(self):
        zeros = bytes(self.bytes_per_word)
        for page_idx in self.modified_pages:
            start = self.mmap_page_idx_to_addr(page_idx)
            block, block_addr = self.__access_addr_range(
                start, _MMAP_PAGE_SIZE, _MMapPageFlags.R)
            end = start + _MMAP_PAGE_SIZE
            for word_idx in range(start // self.bytes_per_word,
                                    end // self.bytes_per_word):
                next_block_addr = block_addr + self.bytes_per_word
                bytes_ = block[block_addr:next_block_addr]
                block_addr = next_block_addr
                if bytes_ != zeros:
                    yield word_idx

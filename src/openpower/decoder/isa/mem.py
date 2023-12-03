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
from openpower.util import log, LogType
import math
import enum
from cached_property import cached_property
import mmap
import struct
from pickle import PicklingError
import ctypes
from nmutil import plain_data
from pathlib import Path
from openpower.syscalls import ppc_flags
import os
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import P_FLAGS


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
            return MMapPageFlags.X
        return MMapPageFlags.R

    @cached_property
    def ld_logs(self):
        return self is not self.Dump


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
        if isinstance(initial_mem, ELFFile):
            return load_elf(self, initial_mem)
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

    def make_sim_state_dict(self):
        """ returns a dict equivalent to:
        retval = {}
        for k in list(self.word_idxs()):
            data = self.ld(k*8, 8, False)
            retval[k*8] = data
        """
        retval = {}
        for k in list(self.word_idxs()):
            data = self.ld(k*8, 8, False, reason=_ReadReason.Dump)
            retval[k*8] = data
        return retval

    def _get_shifter_mask(self, wid, remainder, do_log=True):
        shifter = ((self.bytes_per_word - wid) - remainder) * \
            8  # bits per byte
        # XXX https://bugs.libre-soc.org/show_bug.cgi?id=377
        # BE/LE mode?
        shifter = remainder * 8
        mask = (1 << (wid * 8)) - 1
        if do_log:
            log("width,rem,shift,mask",
                wid, remainder, hex(shifter), hex(mask))
        return shifter, mask

    # TODO: Implement ld/st of lesser width
    def ld(self, address, width=8, swap=True, check_in_mem=False,
           instr_fetch=False, reason=None):
        do_log = reason is not None and reason.ld_logs
        if do_log:
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
        if do_log:
            log("ld mem @ 0x%x rem %d : 0x%x" % (ldaddr, remainder, val))

        if width != self.bytes_per_word:
            shifter, mask = self._get_shifter_mask(width, remainder, do_log)
            if do_log:
                log("masking", hex(val), hex(mask << shifter), shifter)
            val = val & (mask << shifter)
            val >>= shifter
        if swap:
            val = swap_order(val, width)
        if do_log:
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
        log("v, val2", hex(v), hex(val2), "ad", addr2)
        self._st(addr2, val2, width=width-misaligned, swap=False)

    def __call__(self, addr, sz):
        val = self.ld(addr.value, sz, swap=False)
        log("memread", addr, sz, hex(val), kind=LogType.InstrInOuts)
        return SelectableInt(val, sz*8)

    def memassign(self, addr, sz, val):
        log("memassign", addr, sz, val, kind=LogType.InstrInOuts)
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

    def log_fancy(self, *, kind=LogType.Default, name="Memory",
                  log2_line_size=4, log2_column_chunk_size=3, log=log):
        line_size = 1 << log2_line_size
        subline_mask = line_size - 1
        column_chunk_size = 1 << log2_column_chunk_size

        def make_line():
            return bytearray(line_size)
        mem_lines = defaultdict(make_line)
        subword_range = range(1 << self.word_log2)
        words = self.make_sim_state_dict()
        for addr, word in words.items():
            for i in subword_range:
                v = (word >> i * 8) & 0xFF
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


class MMapPageFlags(enum.IntFlag):
    """ flags on each mmap-ped page

    Note: these are *not* PowerISA MMU pages, but instead internal to Mem so
    it can detect invalid accesses and assert rather than segfaulting.
    """
    R = 1
    W = 2
    X = 4
    "readable when instr_fetch=True"

    S = 8
    "shared -- aka. not copy-on-write"

    GROWS_DOWN = 16
    """this memory block will grow when the address one page before the
    beginning is accessed"""

    RW = R | W
    RWX = RW | X
    NONE = 0


_ALLOWED_MMAP_NORMAL_FLAGS = MMapPageFlags.RWX | MMapPageFlags.S
_ALLOWED_MMAP_STACK_FLAGS = MMapPageFlags.RWX | MMapPageFlags.GROWS_DOWN


MMAP_PAGE_SIZE = 1 << 16  # size of chunk that we track
_PAGE_COUNT = (1 << 48) // MMAP_PAGE_SIZE  # 48-bit address space
_NEG_PG_IDX_START = _PAGE_COUNT // 2  # start of negative half of address space
_USER_SPACE_SIZE = _NEG_PG_IDX_START * MMAP_PAGE_SIZE

# code assumes BLOCK_SIZE is a power of two
# BLOCK_SIZE = 1 << 32
BLOCK_SIZE = 1 << 28  # reduced so it works on armv7a

assert BLOCK_SIZE % MMAP_PAGE_SIZE == 0
assert MMAP_PAGE_SIZE % mmap.PAGESIZE == 0, "host's page size is too big"
assert 2 ** (mmap.PAGESIZE.bit_length() - 1) == mmap.PAGESIZE, \
    "host's page size isn't a power of 2"

def _make_default_block_addrs():
    needed_page_addrs = (
        0,  # low end of user space
        0x10000000, # default ELF load address
        _USER_SPACE_SIZE - MMAP_PAGE_SIZE,  # high end of user space
    )
    block_addrs = set()
    for page_addr in needed_page_addrs:
        offset = page_addr % BLOCK_SIZE
        block_addrs.add(page_addr - offset)
    return tuple(sorted(block_addrs))

DEFAULT_BLOCK_ADDRS = _make_default_block_addrs()


@plain_data.plain_data(frozen=True, unsafe_hash=True, repr=False)
class MMapEmuBlock:
    __slots__ = ("addrs", "flags", "file", "file_off")

    def __init__(self, addrs, flags=MMapPageFlags.NONE, file=None, file_off=0):
        # type: (range, MMapPageFlags, Path | str | None, int) -> None
        if addrs.step != 1:
            raise ValueError("bad address range, step must be 1")
        if len(addrs) <= 0:
            raise ValueError("bad address range, must be non-empty")
        if addrs.start < 0:
            raise ValueError("bad address range, must be non-negative")
        if addrs.stop > 2 ** 64:
            raise ValueError("bad address range -- goes beyond 2 ** 64")
        if addrs.start % MMAP_PAGE_SIZE:
            raise ValueError("bad address range -- start isn't page-aligned")
        if addrs.stop % MMAP_PAGE_SIZE:
            raise ValueError("bad address range -- stop isn't page-aligned")
        if addrs[0] // BLOCK_SIZE != addrs[-1] // BLOCK_SIZE:
            raise ValueError(
                "bad address range -- crosses underlying block boundaries")
        if file is not None:
            if file_off < 0:
                raise ValueError("bad file_off, must be non-negative")
            if file_off % MMAP_PAGE_SIZE:
                raise ValueError("bad file_off, must be page-aligned")
            if flags & ~_ALLOWED_MMAP_NORMAL_FLAGS:
                raise ValueError("invalid flags for mmap with file")
            file = Path(file)
        else:
            if flags & ~_ALLOWED_MMAP_NORMAL_FLAGS:
                if flags & ~_ALLOWED_MMAP_STACK_FLAGS:
                    raise ValueError("invalid flags for anonymous mmap")
            file_off = 0  # no file -- clear offset
        self.addrs = addrs
        self.flags = flags
        self.file = file
        self.file_off = file_off
        self.page_indexes  # check that addresses can be mapped to pages

    def intersects(self, other):
        # type: (MMapEmuBlock | range) -> bool
        if isinstance(other, MMapEmuBlock):
            other = other.addrs
        if len_(other) == 0:
            return False
        return other.start < self.addrs.stop and self.addrs.start < other.stop

    @property
    def is_private_anon(self):
        return self.file is None and not self.flags & MMapPageFlags.S

    @property
    def underlying_block_key(self):
        offset = self.addrs.start % BLOCK_SIZE
        return self.addrs.start - offset

    @property
    def underlying_block_offsets(self):
        start = self.addrs.start % BLOCK_SIZE
        return range(start, start + len(self.addrs))

    @property
    def page_indexes(self):
        first_page = MemMMap.addr_to_mmap_page_idx(self.addrs[0])
        # can't just use stop, since that may be out-of-range
        last_page = MemMMap.addr_to_mmap_page_idx(self.addrs[-1])
        if first_page < _NEG_PG_IDX_START and last_page >= _NEG_PG_IDX_START:
            raise ValueError(
                "bad address range, crosses transition from positive "
                "canonical addresses to negative canonical addresses")
        return range(first_page, last_page + 1)

    def difference(self, remove):
        # type: (MMapEmuBlock) -> list[MMapEmuBlock]
        """returns the blocks left after removing `remove` from `self`"""
        if not self.intersects(remove):
            return [self]
        retval = []
        addrs = range(self.addrs.start, remove.addrs.start)
        if len(addrs):
            retval.append(plain_data.replace(self, addrs=addrs))
        addrs = range(remove.addrs.stop, self.addrs.stop)
        if len(addrs):
            file_off = self.file_off + addrs.start - self.addrs.start
            retval.append(plain_data.replace(
                self, addrs=addrs, file_off=file_off))
        return retval

    def __repr__(self):
        parts = ["MMapEmuBlock(range(0x%X, 0x%X)"
                 % (self.addrs.start, self.addrs.stop)]
        if self.flags != MMapPageFlags.NONE:
            parts.append(", flags=%r" % (self.flags, ))
        if self.file is not None:
            parts.append(", file=%r" % (self.file, ))
        if self.file_off != 0:
            parts.append(", file_off=0x%X" % (self.file_off, ))
        parts.append(")")
        return "".join(parts)


# stuff marked "not available" is not in the powerpc64le headers on my system
LEGACY_MAP_MASK = (
    ppc_flags.MAP_SHARED
    | ppc_flags.MAP_PRIVATE
    | ppc_flags.MAP_FIXED
    | ppc_flags.MAP_ANONYMOUS
    | ppc_flags.MAP_DENYWRITE
    | ppc_flags.MAP_EXECUTABLE
    # | ppc_flags.MAP_UNINITIALIZED  # not available -- ignored for now
    | ppc_flags.MAP_GROWSDOWN
    | ppc_flags.MAP_LOCKED
    | ppc_flags.MAP_NORESERVE
    | ppc_flags.MAP_POPULATE
    | ppc_flags.MAP_NONBLOCK
    | ppc_flags.MAP_STACK
    | ppc_flags.MAP_HUGETLB
    # | ppc_flags.MAP_32BIT  # not available -- ignored for now
    # | ppc_flags.MAP_ABOVE4G  # not available -- ignored for now
    # | ppc_flags.MAP_HUGE_2MB  # not available -- ignored for now
    # | ppc_flags.MAP_HUGE_1GB  # not available -- ignored for now
)

_MAP_GROWS = ppc_flags.MAP_GROWSDOWN
# _MAP_GROWS |= ppc_flags.MAP_GROWSUP  # not available -- ignored for now

def len_(r):
    """ len(), but with fix for len(range(2**64)) raising OverflowError """
    try:
        return len(r)
    except OverflowError:
        assert isinstance(r, range)
        return 1 + (r.stop - r.start - 1) // r.step


class MemMMap(MemCommon):
    def __init__(self, row_bytes=8, initial_mem=None, misaligned_ok=False,
                 block_addrs=DEFAULT_BLOCK_ADDRS, emulating_mmap=False):
        # we can't allocate the entire 2 ** 47 byte address space, so split
        # it into smaller blocks
        self.mem_blocks = {
            addr: mmap.mmap(-1, BLOCK_SIZE) for addr in sorted(block_addrs)}
        assert all(addr % BLOCK_SIZE == 0 for addr in self.mem_blocks), \
            "misaligned block address not supported"
        self.__page_flags = {}
        self.modified_pages = set()
        self.__heap_range = None
        self.__mmap_emu_alloc_blocks = set()  # type: set[MMapEmuBlock] | None

        for addr, block in self.mem_blocks.items():
            block_addr = ctypes.addressof(ctypes.c_ubyte.from_buffer(block))
            log("0x%X -> 0x%X len=0x%X" % (addr, block_addr, BLOCK_SIZE))

        # build the list of unbacked blocks -- those address ranges that have
        # no backing memory so mmap can't allocate there. These are maintained
        # separately from __mmap_emu_alloc_blocks so munmap/mremap can't
        # remove/modify them
        addr_ranges = [
            range(a, a + len(b)) for a, b in self.mem_blocks.items()]
        self.__mmap_emu_unbacked_blocks = tuple(self.__gaps_in(addr_ranges))

        if not emulating_mmap:
            self.__mmap_emu_alloc_blocks = None
            # mark blocks as readable/writable
            for addr, block in self.mem_blocks.items():
                start_page = self.addr_to_mmap_page_idx(addr)
                end_page = start_page + len(block) // MMAP_PAGE_SIZE
                for page_idx in range(start_page, end_page):
                    self.__page_flags[page_idx] = MMapPageFlags.RWX

        super().__init__(row_bytes, initial_mem, misaligned_ok)

    @property
    def heap_range(self):
        # type: () -> range | None
        return self.__heap_range

    @heap_range.setter
    def heap_range(self, value):
        # type: (range | None) -> None
        if value is None:
            self.__heap_range = value
            return
        if not self.emulating_mmap:
            raise ValueError(
                "can't set heap_range without emulating_mmap=True")
        if not isinstance(value, range):
            raise TypeError("heap_range must be a range or None")
        if value.step != 1 or value.start > value.stop:
            raise ValueError("heap_range is not a suitable range")
        if value.start % MMAP_PAGE_SIZE != 0:
            raise ValueError("heap_range.start must be aligned")
        if value.stop % MMAP_PAGE_SIZE != 0:
            raise ValueError("heap_range.stop must be aligned")
        self.__heap_range = value

    @staticmethod
    def __gaps_in(sorted_ranges, start=0, stop=2 ** 64):
        # type: (list[range] | tuple[range], int, int) -> list[range]
        start = 0
        gaps = []
        for r in sorted_ranges:
            gap = range(start, r.start)
            if len(gap):
                gaps.append(gap)
            start = r.stop
        gap = range(start, stop)
        if len_(gap):
            gaps.append(gap)
        return gaps

    @property
    def emulating_mmap(self):
        return self.__mmap_emu_alloc_blocks is not None

    def __mmap_emu_map_fixed(self, block, replace, dry_run):
        # type: (MMapEmuBlock, bool, bool) -> bool
        """insert the block at the fixed address passed in, replacing the
        parts of any other blocks that overlap if `replace` is `True`.

        If `dry_run`, then don't make any changes, just check if it would
        succeed.

        This function requires the caller to check `block`'s permissions and to
        perform the underlying `mmap` first.
        """
        if block.underlying_block_key not in self.mem_blocks:
            return False  # unbacked block
        # intersecting_blocks must be separate list so we don't iterate while
        # we modify self.__mmap_emu_alloc_blocks
        intersecting_blocks = [
            b for b in self.__mmap_emu_alloc_blocks if block.intersects(b)]
        for b in intersecting_blocks:
            if not replace:
                return False
            if not dry_run:
                self.__mmap_emu_alloc_blocks.remove(b)
                for replacement in b.difference(block):
                    self.__mmap_emu_alloc_blocks.add(replacement)
        if not dry_run:
            self.__mmap_emu_alloc_blocks.add(block)
            for page_idx in block.page_indexes:
                self.__page_flags[page_idx] = block.flags
        return True

    def __mmap_emu_unmap(self, block):
        # type: (MMapEmuBlock) -> int
        """unmap `block`, return 0 if no error, otherwise return -errno"""
        assert block in self.__mmap_emu_alloc_blocks, \
            "can't unmap already unmapped block"

        # replace mapping with zeros
        retval = self.__mmap_emu_zero_block(block)
        if retval < 0:
            return retval
        # remove block
        self.__mmap_emu_alloc_blocks.remove(block)
        # mark pages as empty
        for page_idx in block.page_indexes:
            self.__page_flags.pop(page_idx)
            self.modified_pages.remove(page_idx)
        return retval

    def __mmap_emu_zero_block(self, block):
        # type: (MMapEmuBlock) -> int
        """ mmap zeros over block, return 0 if no error,
        otherwise return -errno
        """
        mblock = self.mem_blocks[block.underlying_block_key]
        offsets = block.underlying_block_offsets
        buf = (ctypes.c_ubyte * len(offsets)).from_buffer(mblock, offsets[0])
        buf_addr = ctypes.addressof(buf)
        libc = ctypes.CDLL(None)
        syscall = libc.syscall
        syscall.restype = ctypes.c_long
        syscall.argtypes = (ctypes.c_long,) * 6
        call_no = ctypes.c_long(ppc_flags.host_defines['SYS_mmap'])
        host_prot = ppc_flags.host_defines['PROT_READ']
        host_prot |= ppc_flags.host_defines['PROT_WRITE']
        host_flags = ppc_flags.host_defines['MAP_ANONYMOUS']
        host_flags |= ppc_flags.host_defines['MAP_FIXED']
        host_flags |= ppc_flags.host_defines['MAP_PRIVATE']
        # map a block of zeros over it
        if -1 == int(syscall(
                call_no, ctypes.c_long(buf_addr),
                ctypes.c_long(len(offsets)),
                ctypes.c_long(host_prot), ctypes.c_long(host_flags),
                ctypes.c_long(-1), ctypes.c_long(0))):
            return -ctypes.get_errno()
        return 0

    def __mmap_emu_resize_map_fixed(self, block, new_size):
        # type: (MMapEmuBlock, int) -> MMapEmuBlock | None
        assert block in self.__mmap_emu_alloc_blocks, \
            "can't resize unmapped block"
        if new_size == len(block.addrs):
            return block
        addrs = range(block.addrs.start, block.addrs.start + new_size)
        new_block = plain_data.replace(block, addrs=addrs)
        self.__mmap_emu_alloc_blocks.remove(block)
        try:
            if not self.__mmap_emu_map_fixed(
                    new_block, replace=False, dry_run=True):
                return None
        finally:
            self.__mmap_emu_alloc_blocks.add(block)
        if not block.is_private_anon:
            # FIXME: implement resizing underlying mapping
            raise NotImplementedError
        else:
            # clear newly mapped bytes
            clear_addrs = range(block.addrs.stop, new_block.addrs.stop)
            if len_(clear_addrs):
                clear_block = MMapEmuBlock(clear_addrs)
                if self.__mmap_emu_zero_block(clear_block) < 0:
                    return None

        if new_size < len(block.addrs):
            # shrinking -- unmap pages at end
            r = range(new_block.page_indexes.stop, block.page_indexes.stop)
            clear_block = MMapEmuBlock(r)
            if self.__mmap_emu_zero_block(clear_block) < 0:
                return None
            for page_idx in r:
                self.__page_flags.pop(page_idx)
                self.modified_pages.remove(page_idx)
        else:
            # expanding -- map pages at end, they're cleared already
            r = range(block.page_indexes.stop, new_block.page_indexes.stop)
            for page_idx in r:
                self.__page_flags[page_idx] = block.flags
                self.modified_pages.remove(page_idx)  # cleared page
        self.__mmap_emu_alloc_blocks.remove(block)
        self.__mmap_emu_alloc_blocks.add(new_block)
        return new_block

    def __mmap_emu_find_free_addr(self, block):
        # type: (MMapEmuBlock) -> MMapEmuBlock | None
        """find a spot where `block` will fit, returning the new block"""
        blocks = [*self.__mmap_emu_alloc_blocks,
                  *self.__mmap_emu_unbacked_blocks]
        blocks.sort(key=lambda b: b.addrs.start)
        biggest_gap = range(0)
        for gap in self.__gaps_in([b.addrs for b in blocks]):
            if len(biggest_gap) < len(gap):
                biggest_gap = gap
        extra_size = len(biggest_gap) - len(block.addrs)
        if extra_size < 0:
            return None  # no space anywhere
        # try to allocate in the middle of the gap, so mmaps can grow later
        offset = extra_size // 2

        # align to page -- this depends on gap being aligned already.
        #
        # rounds down offset, so no need to check size again since it can't
        # ever get closer to the end of the gap
        offset -= offset % MMAP_PAGE_SIZE
        start = biggest_gap.start + offset
        addrs = range(start, start + len(block))
        return plain_data.replace(block, addrs=addrs)

    def __mmap_emu_try_grow_down(self, addr, needed_flag):
        # type: (int, MMapPageFlags) -> bool
        """ if addr is the page just before a GROW_DOWN block, try to grow it.
        returns True if successful. """
        return False  # FIXME: implement

    def brk_syscall(self, addr):
        assert self.emulating_mmap, "brk syscall requires emulating_mmap=True"
        assert self.heap_range is not None, "brk syscall requires a heap"

        if addr < self.heap_range.start:
            # can't shrink heap to negative size
            return self.heap_range.stop  # don't change heap

        # round addr up to the nearest page
        addr_div_page_size = -(-addr // MMAP_PAGE_SIZE)  # ceil(addr / size)
        addr = addr_div_page_size * MMAP_PAGE_SIZE

        # something else could be mmap-ped in the middle of the heap,
        # be careful...

        block = None
        if len_(self.heap_range) != 0:
            for b in self.__mmap_emu_alloc_blocks:
                # we check for the end matching so we get the last heap block
                # if the heap was split.
                # the heap must not be a file mapping.
                # the heap must not be shared, and must be RW
                if b.addrs.stop == self.heap_range.stop and b.file is None \
                        and b.flags == MMapPageFlags.RW:
                    block = b
                    break

        if block is not None and addr < block.addrs.start:
            # heap was split by something, we can't shrink beyond
            # the start of the last heap block
            return self.heap_range.stop  # don't change heap

        if block is not None and addr == block.addrs.start:
            # unmap heap block
            if self.__mmap_emu_unmap(block) < 0:
                block = None  # can't unmap heap block
        elif addr > self.heap_range.stop and block is None:
            # map new heap block
            try:
                addrs = range(self.heap_range.stop, addr)
                block = MMapEmuBlock(addrs, flags=MMapPageFlags.RW)
                if not self.__mmap_emu_map_fixed(block,
                                                 replace=False, dry_run=True):
                    block = None
                elif 0 != self.__mmap_emu_zero_block(block):
                    block = None
                else:
                    self.__mmap_emu_map_fixed(block,
                                              replace=False, dry_run=False)
            except (MemException, ValueError):
                # caller could pass in invalid size, catch that
                block = None
        elif block is not None:  # resize block
            try:
                block = self.__mmap_emu_resize_map_fixed(
                    block, addr - block.addrs.start)
            except (MemException, ValueError):
                # caller could pass in invalid size, catch that
                block = None

        if block is None and addr != self.heap_range.start:
            # can't resize heap block
            return self.heap_range.stop  # don't change heap

        # success! assign new heap_range
        self.heap_range = range(self.heap_range.start, addr)
        return self.heap_range.stop  # return new brk address

    def mmap_syscall(self, addr, length, prot, flags, fd, offset, is_mmap2):
        assert self.emulating_mmap, "mmap syscall requires emulating_mmap=True"
        if is_mmap2:
            offset *= 4096  # specifically *not* the page size
        prot_read = bool(prot & ppc_flags.PROT_READ)
        prot_write = bool(prot & ppc_flags.PROT_WRITE)
        prot_exec = bool(prot & ppc_flags.PROT_EXEC)
        prot_all = (ppc_flags.PROT_READ | ppc_flags.PROT_WRITE
                    | ppc_flags.PROT_EXEC)
        # checks based off the checks in linux
        if prot & ~prot_all:
            return -ppc_flags.EINVAL
        if offset % MMAP_PAGE_SIZE:
            return -ppc_flags.EINVAL
        if flags & ppc_flags.MAP_HUGETLB:
            # not supported
            return -ppc_flags.EINVAL
        if length <= 0 or offset < 0:
            return -ppc_flags.EINVAL
        if flags & ppc_flags.MAP_FIXED_NOREPLACE:
            flags |= ppc_flags.MAP_FIXED
        if not (flags & ppc_flags.MAP_FIXED):
            addr &= MMAP_PAGE_SIZE - 1  # page-align address, rounding down
        # page-align length, rounding up
        length = (length + MMAP_PAGE_SIZE - 1) & ~(MMAP_PAGE_SIZE - 1)
        if length + offset >= 2 ** 64:
            # overflowed
            return -ppc_flags.ENOMEM
        block_flags = MMapPageFlags.NONE
        if prot_read:
            block_flags |= MMapPageFlags.R
        if prot_write:
            block_flags |= MMapPageFlags.W
        if prot_exec:
            block_flags |= MMapPageFlags.X
        if flags & ppc_flags.MAP_GROWSDOWN:
            block_flags |= MMapPageFlags.GROWS_DOWN
        file = None
        if fd >= 0:
            try:
                file = os.readlink("/proc/self/fd/%i" % fd)
            except IOError:
                return -ppc_flags.EBADF
        try:
            block = MMapEmuBlock(
                range(addr, addr + length), block_flags, file, offset)
        except (ValueError, MemException):
            return -ppc_flags.EINVAL
        if not (flags & ppc_flags.MAP_FIXED):
            block = self.__mmap_emu_find_free_addr(block)
            if block is None:
                return -ppc_flags.ENOMEM
        if flags & ppc_flags.MAP_LOCKED:
            return -ppc_flags.EPERM
        map_ty = flags & ppc_flags.MAP_TYPE
        if file is not None:
            fallthrough = False
            if map_ty == ppc_flags.MAP_SHARED:
                flags &= LEGACY_MAP_MASK
                fallthrough = True
            if fallthrough or map_ty == ppc_flags.MAP_SHARED_VALIDATE:
                if flags & ~LEGACY_MAP_MASK:
                    return -ppc_flags.EOPNOTSUPP
                raise NotImplementedError("MAP_SHARED on file")
                fallthrough = True
            if fallthrough or map_ty == ppc_flags.MAP_PRIVATE:
                if flags & _MAP_GROWS:
                    return -ppc_flags.EINVAL
            else:
                return -ppc_flags.EINVAL
        elif map_ty == ppc_flags.MAP_SHARED:
            if flags & _MAP_GROWS:
                return -ppc_flags.EINVAL
            raise NotImplementedError("MAP_SHARED on memory")
        elif map_ty != ppc_flags.MAP_PRIVATE:
            return -ppc_flags.EINVAL
        replace = not (flags & ppc_flags.MAP_FIXED_NOREPLACE)
        if not self.__mmap_emu_map_fixed(block, replace, dry_run=True):
            # failed, was that because there's an existing memory block or
            # that was an invalid address?
            if self.__mmap_emu_map_fixed(block, replace=True, dry_run=True):
                return -ppc_flags.EEXIST  # existing memory block
            else:
                return -ppc_flags.EINVAL  # invalid address
        mblock = self.mem_blocks[block.underlying_block_key]
        offsets = block.underlying_block_offsets
        buf = (ctypes.c_ubyte * len(offsets)).from_buffer(mblock, offsets[0])
        buf_addr = ctypes.addressof(buf)
        libc = ctypes.CDLL(None)
        syscall = libc.syscall
        syscall.restype = ctypes.c_long
        syscall.argtypes = (ctypes.c_long,) * 6
        call_no = ctypes.c_long(ppc_flags.host_defines['SYS_mmap'])
        host_prot = ppc_flags.host_defines['PROT_READ']
        if block.flags & MMapPageFlags.W:
            host_prot |= ppc_flags.host_defines['PROT_WRITE']
        host_flags = ppc_flags.host_defines['MAP_FIXED']
        host_flags |= ppc_flags.host_defines['MAP_PRIVATE']
        length = len(offsets)
        extra_zeros_length = 0
        extra_zeros_start = 0
        if file is None:
            host_flags |= ppc_flags.host_defines['MAP_ANONYMOUS']
            # don't remove check, since we'll eventually have shared memory
            if host_flags & ppc_flags.host_defines['MAP_PRIVATE']:
                # always map private memory read/write,
                # so we can clear it if needed
                host_prot |= ppc_flags.host_defines['PROT_WRITE']
        else:
            file_sz = os.fstat(fd).st_size
            # host-page-align file_sz, rounding up
            file_sz = (file_sz + mmap.PAGESIZE - 1) & ~(mmap.PAGESIZE - 1)
            extra_zeros_length = max(0, length - (file_sz - offset))
            extra_zeros_start = buf_addr + (file_sz - offset)
            length -= extra_zeros_length
        res = int(syscall(
            call_no, ctypes.c_long(buf_addr), ctypes.c_long(length),
            ctypes.c_long(host_prot), ctypes.c_long(host_flags),
            ctypes.c_long(fd), ctypes.c_long(offset)))
        if res == -1:
            return -ctypes.get_errno()
        self.__mmap_emu_map_fixed(block, replace=True, dry_run=False)
        if extra_zeros_length != 0:
            host_flags = ppc_flags.host_defines['MAP_ANONYMOUS']
            host_flags |= ppc_flags.host_defines['MAP_FIXED']
            host_flags |= ppc_flags.host_defines['MAP_PRIVATE']
            if -1 == int(syscall(
                    call_no, ctypes.c_long(extra_zeros_start),
                    ctypes.c_long(extra_zeros_length),
                    ctypes.c_long(host_prot), ctypes.c_long(host_flags),
                    ctypes.c_long(-1), ctypes.c_long(0))):
                return -ctypes.get_errno()
        if file is not None:
            # memory could be non-zero, mark as modified
            for page_idx in block.page_indexes:
                self.modified_pages.add(page_idx)
        log("mmap block=%s" % (block,), kind=LogType.InstrInOuts)
        return block.addrs.start

    @staticmethod
    def mmap_page_idx_to_addr(page_idx):
        assert 0 <= page_idx < _PAGE_COUNT
        if page_idx >= _NEG_PG_IDX_START:
            page_idx -= _PAGE_COUNT
        return (page_idx * MMAP_PAGE_SIZE) % 2 ** 64

    @staticmethod
    def addr_to_mmap_page_idx(addr):
        page_idx, offset = divmod(addr, MMAP_PAGE_SIZE)
        page_idx %= _PAGE_COUNT
        expected = MemMMap.mmap_page_idx_to_addr(page_idx) + offset
        if addr != expected:
            exc = MemException("not sign extended",
                               ("address not sign extended: 0x%X "
                                "expected 0x%X") % (addr, expected))
            exc.dar = addr
            raise exc
        return page_idx

    def __reduce_ex__(self, protocol):
        raise PicklingError("MemMMap can't be deep-copied or pickled")

    def __access_addr_range_err(self, start_addr, size, needed_flag):
        assert needed_flag != MMapPageFlags.W, \
            "can't write to address 0x%X size 0x%X" % (start_addr, size)
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
            flags = self.__page_flags.get(i, 0)
            if flags & needed_flag == 0:
                if not self.__mmap_emu_try_grow_down(start_addr, needed_flag):
                    return self.__access_addr_range_err(
                        start_addr, size, needed_flag)
            if needed_flag is MMapPageFlags.W:
                self.modified_pages.add(page_idx)
        return self.mem_blocks[block_k], block_addr

    def get_ctypes(self, start_addr, size, is_write):
        """ returns a ctypes ubyte array referring to the memory at
        `start_addr` with size `size`
        """
        flag = MMapPageFlags.W if is_write else MMapPageFlags.R
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
            MMapPageFlags.W)
        bytes_ = value.to_bytes(self.bytes_per_word, 'little')
        block[block_addr:block_addr + self.bytes_per_word] = bytes_

    def word_idxs(self):
        zeros = bytes(self.bytes_per_word)
        for page_idx in self.modified_pages:
            start = self.mmap_page_idx_to_addr(page_idx)
            block, block_addr = self.__access_addr_range(
                start, MMAP_PAGE_SIZE, MMapPageFlags.R)
            end = start + MMAP_PAGE_SIZE
            for word_idx in range(start // self.bytes_per_word,
                                  end // self.bytes_per_word):
                next_block_addr = block_addr + self.bytes_per_word
                bytes_ = block[block_addr:next_block_addr]
                block_addr = next_block_addr
                if bytes_ != zeros:
                    yield word_idx

    def make_sim_state_dict(self):
        """ returns a dict equivalent to:
        retval = {}
        for k in list(self.word_idxs()):
            data = self.ld(k*8, 8, False)
            retval[k*8] = data
        """
        if self.bytes_per_word != 8:
            return super().make_sim_state_dict()
        retval = {}
        page_struct = struct.Struct("<%dQ" % (MMAP_PAGE_SIZE // 8,))
        assert page_struct.size == MMAP_PAGE_SIZE, "got wrong format"
        for page_idx in self.modified_pages:
            start = self.mmap_page_idx_to_addr(page_idx)
            block, block_addr = self.__access_addr_range(
                start, MMAP_PAGE_SIZE, MMapPageFlags.R)
            # written this way to avoid unnecessary allocations
            words = page_struct.unpack_from(block, block_addr)
            for i, v in zip(range(start, start + MMAP_PAGE_SIZE, 8), words):
                if v != 0:
                    retval[i] = v
        return retval


@plain_data.plain_data()
class LoadedELF:
    __slots__ = "elf_file", "pc", "gprs", "fpscr"

    def __init__(self, elf_file, pc, gprs, fpscr):
        self.elf_file = elf_file
        self.pc = pc
        self.gprs = gprs
        self.fpscr = fpscr


def raise_if_syscall_err(result):
    if -4096 < result < 0:
        raise OSError(-result, os.strerror(-result))
    return result


# TODO: change to much smaller size once GROWSDOWN is implemented
DEFAULT_INIT_STACK_SZ = 4 << 20


def load_elf(mem, elf_file, args=(), env=(), stack_size=DEFAULT_INIT_STACK_SZ):
    if not isinstance(mem, MemMMap):
        raise TypeError("MemMMap required to load ELFs")
    if not isinstance(elf_file, ELFFile):
        raise TypeError()
    if elf_file.header['e_type'] != 'ET_EXEC':
        raise NotImplementedError("dynamic binaries aren't implemented")
    fd = elf_file.stream.fileno()
    for segment in elf_file.iter_segments():
        if segment.header['p_type'] in ('PT_DYNAMIC', 'PT_INTERP'):
            raise NotImplementedError("dynamic binaries aren't implemented")
        elif segment.header['p_type'] == 'PT_LOAD':
            flags = segment.header['p_flags']
            offset = segment.header['p_offset']
            vaddr = segment.header['p_vaddr']
            filesz = segment.header['p_filesz']
            memsz = segment.header['p_memsz']
            align = segment.header['p_align']
            if align != 0x10000:
                raise NotImplementedError("non-default ELF segment alignment")
            if align < MMAP_PAGE_SIZE:
                raise NotImplementedError("align less than MMAP_PAGE_SIZE")
            prot = ppc_flags.PROT_NONE
            if flags & P_FLAGS.PF_R:
                prot |= ppc_flags.PROT_READ
            if flags & P_FLAGS.PF_W:
                prot |= ppc_flags.PROT_WRITE
            if flags & P_FLAGS.PF_X:
                prot |= ppc_flags.PROT_EXEC
            # align start to page
            adj = offset % MMAP_PAGE_SIZE
            offset -= adj
            assert offset >= 0
            vaddr -= adj
            filesz += adj
            memsz += adj
            # page-align, rounding up
            filesz_aligned = (
                filesz + MMAP_PAGE_SIZE - 1) & ~(MMAP_PAGE_SIZE - 1)
            page_end_init_needed = filesz < memsz and filesz < filesz_aligned
            zero_pages_needed = memsz > filesz_aligned
            adj_prot = prot  # adjust prot for initialization
            if page_end_init_needed:
                # we need to initialize trailing bytes to zeros,
                # so we need write access
                adj_prot |= ppc_flags.PROT_WRITE
            flags = ppc_flags.MAP_FIXED_NOREPLACE | ppc_flags.MAP_PRIVATE
            result = mem.mmap_syscall(
                vaddr, filesz, adj_prot, flags, fd, offset, is_mmap2=False)
            raise_if_syscall_err(result)
            if page_end_init_needed:
                page_end = mem.get_ctypes(
                    vaddr + filesz, filesz_aligned - filesz, True)
                ctypes.memset(page_end, 0, len(page_end))
            if zero_pages_needed:
                result = mem.mmap_syscall(
                    vaddr + filesz_aligned, memsz - filesz_aligned,
                    prot, flags, fd=-1, offset=0, is_mmap2=False)
                raise_if_syscall_err(result)
        else:
            log("ignoring ELF segment of type " + segment.header['p_type'])
    # page-align stack_size, rounding up
    stack_size = (stack_size + MMAP_PAGE_SIZE - 1) & ~(MMAP_PAGE_SIZE - 1)
    stack_top = _USER_SPACE_SIZE
    stack_low = stack_top - stack_size
    prot = ppc_flags.PROT_READ | ppc_flags.PROT_WRITE
    flags = ppc_flags.MAP_FIXED_NOREPLACE | ppc_flags.MAP_PRIVATE
    result = mem.mmap_syscall(
        stack_low, stack_size, prot, flags, fd=-1, offset=0, is_mmap2=False)
    raise_if_syscall_err(result)
    gprs = {}
    if len(args):
        raise NotImplementedError("allocate argv on the stack")
    else:
        argv = 0
    if len(env):
        raise NotImplementedError("allocate envp on the stack")
    else:
        envp = 0

    # FIXME: incorrect, should point to the aux vector allocated on the stack
    auxv = 0

    # make space for red zone, 512 bytes specified in
    # 64-bit ELF V2 ABI Specification v1.5 section 2.2.3.4
    # https://files.openpower.foundation/s/cfA2oFPXbbZwEBK
    stack_top -= 512

    # align stack_top
    stack_top -= stack_top % 16

    # TODO: dynamically-linked binaries need to use the entry-point of ld.so
    pc = elf_file.header['e_entry']
    gprs[1] = stack_top
    gprs[3] = len(args)  # argc
    gprs[4] = argv
    gprs[5] = envp
    gprs[5] = auxv
    gprs[7] = 0  # termination function pointer
    gprs[12] = pc
    fpscr = 0
    return LoadedELF(elf_file, pc, gprs, fpscr)

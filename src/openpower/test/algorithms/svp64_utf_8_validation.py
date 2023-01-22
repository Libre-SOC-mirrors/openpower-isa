# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

import enum
import re
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.test.state import ExpectedState
from openpower.sv.trans.svp64 import SVP64Asm
from cached_property import cached_property


SVP64_UTF8_VALIDATION_DATA_ADDR = 0x10000


class UTF8FirstTwoBytesError(enum.IntFlag):
    """ Error conditions that are detectable from just the first two bytes in
    a UTF-8 sequence.
    """

    TooLong = 1 << 0
    """ ascii byte followed by a continuation byte """

    TooShort = 1 << 1
    """ leading byte followed by something other than a continuation byte """

    Overlong2 = 1 << 2
    """ value is `< 0x80` but is encoded using 2 bytes """

    Surrogate = 1 << 3
    """ value is a surrogate (`0xD800 <= value <= 0xDFFF`) """

    Overlong3 = 1 << 4
    """ value is `< 0x800` but is encoded using 3 bytes """

    Overlong4OrTooLarge = 1 << 5
    """ value is either:
        * `< 0x10000` but is encoded using 4 bytes
        * or the value is `>= 0x140000` with the first continuation byte
            being `<= 0x8F`

        The rest of the cases where the value is `> 0x10FFFF` are covered by
        `TooLarge`.
    """

    TooLarge = 1 << 6
    """ value is `> 0x10FFFF` with the first continuation byte being `>= 0x90`

        The rest of the cases where the value is `> 0x10FFFF` are covered by
        `Overlong4OrTooLarge`.
    """

    TwoContinuations = 1 << 7
    """ not actually an error -- two continuations in a row """

    AllActualErrors = (TooLong | TooShort | Overlong2 | Surrogate |
                       Overlong3 | Overlong4OrTooLarge | TooLarge)


# look up tables for checking for errors in the first two bytes, the final
# error flags are generated by looking up the nibbles of the first two bytes
# in the appropriate tables, and bitwise ANDing the results together.
# To figure out what to put in each entry in the LUTs, look for all cases
# that could match the comment.

_TLN = UTF8FirstTwoBytesError.TooLong
_TS = UTF8FirstTwoBytesError.TooShort
_O2 = UTF8FirstTwoBytesError.Overlong2
_SG = UTF8FirstTwoBytesError.Surrogate
_O3 = UTF8FirstTwoBytesError.Overlong3
_O4TL = UTF8FirstTwoBytesError.Overlong4OrTooLarge
_TLG = UTF8FirstTwoBytesError.TooLarge
_2C = UTF8FirstTwoBytesError.TwoContinuations

FIRST_BYTE_HIGH_NIBBLE_LUT_ADDR = 0xFF00
FIRST_BYTE_HIGH_NIBBLE_LUT = [
    _TLN,  # first 2 bytes are 0x0? 0x??
    _TLN,  # first 2 bytes are 0x1? 0x??
    _TLN,  # first 2 bytes are 0x2? 0x??
    _TLN,  # first 2 bytes are 0x3? 0x??
    _TLN,  # first 2 bytes are 0x4? 0x??
    _TLN,  # first 2 bytes are 0x5? 0x??
    _TLN,  # first 2 bytes are 0x6? 0x??
    _TLN,  # first 2 bytes are 0x7? 0x??
    _2C,  # first 2 bytes are 0x8? 0x??
    _2C,  # first 2 bytes are 0x9? 0x??
    _2C,  # first 2 bytes are 0xA? 0x??
    _2C,  # first 2 bytes are 0xB? 0x??
    _TS | _O2,  # first 2 bytes are 0xC? 0x??
    _TS,  # first 2 bytes are 0xD? 0x??
    _TS | _SG | _O3,  # first 2 bytes are 0xE? 0x??
    _TS | _O4TL | _TLG,  # first 2 bytes are 0xF? 0x??
]
FIRST_BYTE_LOW_NIBBLE_LUT_ADDR = 0xFF10
FIRST_BYTE_LOW_NIBBLE_LUT = [
    _TLN | _TS | _O2 | _O3 | _O4TL | _2C,  # first 2 bytes are 0x?0 0x??
    _TLN | _TS | _O2 | _2C,  # first 2 bytes are 0x?1 0x??
    _TLN | _TS | _2C,  # first 2 bytes are 0x?2 0x??
    _TLN | _TS | _2C,  # first 2 bytes are 0x?3 0x??
    _TLN | _TS | _TLG | _2C,  # first 2 bytes are 0x?4 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?5 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?6 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?7 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?8 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?9 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?A 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?B 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?C 0x??
    _TLN | _TS | _SG | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?D 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?E 0x??
    _TLN | _TS | _O4TL | _TLG | _2C,  # first 2 bytes are 0x?F 0x??
]
SECOND_BYTE_HIGH_NIBBLE_LUT_ADDR = 0xFF20
SECOND_BYTE_HIGH_NIBBLE_LUT = [
    _TS,  # first 2 bytes are 0x?? 0x0?
    _TS,  # first 2 bytes are 0x?? 0x1?
    _TS,  # first 2 bytes are 0x?? 0x2?
    _TS,  # first 2 bytes are 0x?? 0x3?
    _TS,  # first 2 bytes are 0x?? 0x4?
    _TS,  # first 2 bytes are 0x?? 0x5?
    _TS,  # first 2 bytes are 0x?? 0x6?
    _TS,  # first 2 bytes are 0x?? 0x7?
    _TLN | _O2 | _O3 | _O4TL | _2C,  # first 2 bytes are 0x?? 0x8?
    _TLN | _O2 | _O3 | _TLG | _2C,  # first 2 bytes are 0x?? 0x9?
    _TLN | _O2 | _SG | _TLG | _2C,  # first 2 bytes are 0x?? 0xA?
    _TLN | _O2 | _SG | _TLG | _2C,  # first 2 bytes are 0x?? 0xB?
    _TS,  # first 2 bytes are 0x?? 0xC?
    _TS,  # first 2 bytes are 0x?? 0xD?
    _TS,  # first 2 bytes are 0x?? 0xE?
    _TS,  # first 2 bytes are 0x?? 0xF?
]


def svp64_utf8_validation_asm():
    vec_sz = 8  # limited by number of CR fields implemented in the simulator
    inp_addr = 3
    # cur bytes in r48-r63 -- u64x16
    cur_bytes = 48
    # prev bytes in r45-r47 -- u64x3
    prev_bytes_sz = 3
    prev_bytes = cur_bytes - prev_bytes_sz
    # error flags in r56-r63 -- u64x8
    temp_vec1 = cur_bytes + vec_sz
    # nibbles to look up in r64-r71 -- u64x8
    temp_vec2 = cur_bytes + vec_sz * 2
    temp_vec2_end = temp_vec2 + vec_sz

    def sv_set_0x80_if_ge(out_v, inp_v, temp_s, compare_rhs):
        # type: (int, int, int, int) -> list[str]
        """ generate values with bit 0x80 set if the input vector is
        unsigned `>= compare_rhs`, this assumes `0x80 <= compare_rhs <= 0xFF`
        and the input vector elements are in `0 <= v <= 0xFF`.

        can't use CRs for this, since vectors of CRs used as masks currently
        max out at 4 in the simulator.
        """
        assert 0x80 <= compare_rhs <= 0xFF, \
            "the algorithm only works if compare_rhs is in range"
        max_arg = compare_rhs - 1
        add_arg = 0x80 - compare_rhs
        return [
            f"addi {temp_s}, 0, {max_arg}",
            f"sv.maxu *{out_v}, *{inp_v}, {temp_s}",
            f"sv.addi *{out_v}, *{out_v}, {add_arg}"
        ]
    return [
        # input addr in r3, input length in r4
        f"setvl 0, 0, {prev_bytes_sz}, 0, 1, 1",  # set VL to prev_bytes_sz
        # clear what will go into prev bytes
        f"sv.addi *{cur_bytes + vec_sz - prev_bytes_sz}, 0, 0",
        f"addis 6, 0, {FIRST_BYTE_HIGH_NIBBLE_LUT_ADDR >> 16}",
        f"ori 6, 6, {FIRST_BYTE_HIGH_NIBBLE_LUT_ADDR & 0xFFFF}",
        f"addis 7, 0, {FIRST_BYTE_LOW_NIBBLE_LUT_ADDR >> 16}",
        f"ori 7, 7, {FIRST_BYTE_LOW_NIBBLE_LUT_ADDR & 0xFFFF}",
        f"addis 8, 0, {SECOND_BYTE_HIGH_NIBBLE_LUT_ADDR >> 16}",
        f"ori 8, 8, {SECOND_BYTE_HIGH_NIBBLE_LUT_ADDR & 0xFFFF}",
        f"loop:",
        f"setvl 0, 0, {prev_bytes_sz}, 0, 1, 1",  # set VL to prev_bytes_sz
        # copy prev bytes from end of cur bytes
        f"sv.ori *{prev_bytes}, *{cur_bytes + vec_sz - prev_bytes_sz}, 0",

        # clear cur bytes, so bytes beyond end end up being zeros
        f"setvl 0, 0, {vec_sz}, 0, 1, 1",  # set VL to vec_sz
        f"sv.addi *{cur_bytes}, 0, 0",  # clear cur bytes
        f"setvl. 5, 4, {vec_sz}, 0, 1, 1",  # set VL to min(vec_sz, r4)
        # if no bytes left to load, run final check
        f"bc 12, 2, final_check # beq final_check",
        # sv.lbz/els is buggy, use sv.lbzx instead:
        f"sv.addi *{cur_bytes + 1}, *{cur_bytes}, 1",  # create indexes
        f"sv.lbzx *{cur_bytes}, {inp_addr}, *{cur_bytes}",  # load bytes
        f"setvl 0, 0, {vec_sz}, 0, 1, 1",  # set VL to vec_sz
        # now we can operate on vec_sz byte chunks, branch to `fail` if they
        # don't pass validation.

        # get high nibbles of input shifted by 1 byte
        (f"sv.rldicl *{temp_vec2}, *{cur_bytes - 1}, {64 - 4}, 4"
         f" # sv.srdi *{temp_vec2}, *{cur_bytes - 1}, 4"),
        # look-up nibbles in table, writing to error flags
        f"sv.lbzx *{temp_vec1}, 6, *{temp_vec2}",

        # get low nibbles of input shifted by 1 byte
        # there is no andi without Rc
        # sv.andi. with scalars is buggy, so use a temporary and sv.and
        f"addi 9, 0, {0xF}",
        f"sv.and *{temp_vec2}, *{cur_bytes - 1}, 9",
        # look-up nibbles in table
        f"sv.lbzx *{temp_vec2}, 7, *{temp_vec2}",
        # bitwise and into error flags
        f"sv.and *{temp_vec1}, *{temp_vec1}, *{temp_vec2}",

        # get high nibbles of input
        # srdi *{temp_vec2}, *{cur_bytes}, 4
        f"sv.rldicl *{temp_vec2}, *{cur_bytes}, {64 - 4}, 4",
        # look-up nibbles in table
        f"sv.lbzx *{temp_vec2}, 8, *{temp_vec2}",
        # bitwise and into error flags
        f"sv.and *{temp_vec1}, *{temp_vec1}, *{temp_vec2}",

        # or-reduce error flags into temp_vec2_end
        f"sv.addi {temp_vec2_end}, 0, 0",
        f"sv.ori *{temp_vec2}, *{temp_vec1}, 0",
        f"sv.or *{temp_vec2 + 1}, *{temp_vec2}, *{temp_vec2 + 1}",
        # check for any actual error flags set
        # sv.andi. is buggy, so use sv.and, then compare
        f"addi 9, 0, {UTF8FirstTwoBytesError.AllActualErrors}",
        f"sv.and 9, {temp_vec2_end}, 9",
        f"cmpli 0, 1, 9, 0",
        f"bc 4, 2, fail # bne fail",

        # check for the correct number of continuation bytes for 3/4-byte cases

        # set bit 0x80 (TwoContinuations) if input is >= 0xE0
        *sv_set_0x80_if_ge(out_v=temp_vec2, inp_v=cur_bytes - 2,
                           temp_s=9, compare_rhs=0xE0),
        # xor into error flags
        f"sv.xor *{temp_vec1}, *{temp_vec1}, *{temp_vec2}",
        # set bit 0x80 (TwoContinuations) if input is >= 0xF0
        *sv_set_0x80_if_ge(out_v=temp_vec2, inp_v=cur_bytes - 3,
                           temp_s=9, compare_rhs=0xF0),
        # xor into error flags
        f"sv.xor *{temp_vec1}, *{temp_vec1}, *{temp_vec2}",
        # now bit 0x80 is set in temp_vec1 if there's an error
        # or-reduce into temp_vec2
        f"sv.addi {temp_vec2}, 0, 0",
        f"sv.or *{temp_vec1 + 1}, *{temp_vec1}, *{temp_vec1 + 1}",
        # adjust count/pointer
        f"add 3, 3, 5",  # increment pointer
        f"subf 4, 5, 4",  # decrement count
        # sv.andi. is buggy, so move to r9 first
        f"sv.ori 9, {temp_vec2}, 0",
        f"andi. 9, 9, {0x80}",  # check if any errors
        f"bc 12, 2, loop # beq loop",  # if no errors loop, else fail
        f"fail:",
        f"addi 3, 0, 0",
        f"bclr 20, 0, 0 # blr",
        f"final_check:",

        # need to set VL to 1, here
        # https://bugs.libre-soc.org/show_bug.cgi?id=905
        # (SVP64Single is planned for accessing high-regnumbers as Scalars)
        #
        # setting VL=0 (often set dynamically at runtime in Standard Cray
        # Vectors) is the standard canonical way in Cray Vectors to legitimately
        # request instructions not to be run at all (nops).
        #
        # a workaround for not having SVP64Single right now and still get
        # at the high register numbers (32-127) is to static-set VL=1
        # the alternative is to move cur_bytes to reg numbers 0-31 but
        # 16 regs within the range 0-31 is a lot to ask for.
        f"setvl 0, 0, 1, 0, 1, 1",  # set VL to 1

        # check if prev input is incomplete
        # check if byte 3 bytes from end needed 4 bytes
        f"sv.cmpli 0, 1, {cur_bytes - 3}, {0xF0}",
        f"bc 4, 0, fail # bge fail",
        # check if byte 2 bytes from end needed 3 bytes
        f"sv.cmpli 0, 1, {cur_bytes - 2}, {0xE0}",
        f"bc 4, 0, fail # bge fail",
        # check if byte 1 bytes from end needed 2 bytes
        f"sv.cmpli 0, 1, {cur_bytes - 1}, {0xC0}",
        f"bc 4, 0, fail # bge fail",
        f"addi 3, 0, 1",
        f"bclr 20, 0, 0 # blr",
    ]


def assemble(instructions, start_pc=0):
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

    return Program(list(SVP64Asm(out_instructions)), 0)


class SVP64UTF8ValidationTestCase(TestAccumulatorBase):
    def __init__(self):
        self.__seen_cases = set()
        super().__init__()

    @cached_property
    def program(self):
        return assemble(svp64_utf8_validation_asm())

    def run_case(self, data, src_loc_at=0):
        # type: (bytes, int) -> None
        if data in self.__seen_cases:
            return
        self.__seen_cases.add(data)
        expected = 1
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            expected = 0
        initial_regs = [0x15cee3293aa9bfbe] * 128  # fill with junk
        initial_regs[3] = 0x10000  # pointer to bytes to check
        initial_regs[4] = len(data)  # length of bytes to check

        initial_mem = {}
        for i, v in enumerate(data):
            initial_mem[i + initial_regs[3]] = v, 1
        for i, v in enumerate(FIRST_BYTE_LOW_NIBBLE_LUT):
            initial_mem[i + FIRST_BYTE_LOW_NIBBLE_LUT_ADDR] = int(v), 1
        for i, v in enumerate(FIRST_BYTE_HIGH_NIBBLE_LUT):
            initial_mem[i + FIRST_BYTE_HIGH_NIBBLE_LUT_ADDR] = int(v), 1
        for i, v in enumerate(SECOND_BYTE_HIGH_NIBBLE_LUT):
            initial_mem[i + SECOND_BYTE_HIGH_NIBBLE_LUT_ADDR] = int(v), 1
        stop_at_pc = 0x10000000
        initial_sprs = {8: SelectableInt(stop_at_pc, 64)}
        e = ExpectedState(pc=stop_at_pc, int_regs=4, crregs=0, fp_regs=0,
                          so=None, ov=None, ca=None)
        e.intregs[:3] = initial_regs[:3]
        e.intregs[3] = expected
        with self.subTest(data=data, expected=expected):
            self.add_case(self.program, initial_regs, initial_mem=initial_mem,
                          initial_sprs=initial_sprs, stop_at_pc=stop_at_pc,
                          expected=e,
                          src_loc_at=src_loc_at + 1)

    def run_cases(self, data):
        # type: (bytes | str) -> None
        if isinstance(data, str):
            data = data.encode("utf-8")
        data = data.center(8, b' ')
        for i in range(len(data)):
            self.run_case(data[i:], src_loc_at=1)
            self.run_case(data[:i], src_loc_at=1)

    def case_empty(self):
        self.run_case(b"")

    def case_x6_sp_nul(self):
        self.run_case(b' ' * 6 + b'\x00')

    def case_nul(self):
        self.run_cases("\u0000")  # min 1-byte

    def case_a(self):
        self.run_cases("a")

    def case_7f(self):
        self.run_cases("\u007F")  # max 1-byte

    def case_c0_80(self):
        self.run_cases(b"\xC0\x80")  # min 2-byte overlong encoding

    def case_c1_bf(self):
        self.run_cases(b"\xC1\xBF")  # max 2-byte overlong encoding

    def case_u0080(self):
        self.run_cases("\u0080")  # min 2-byte

    def case_u07ff(self):
        self.run_cases("\u07FF")  # max 2-byte

    def case_e0_80_80(self):
        self.run_cases(b"\xE0\x80\x80")  # min 3-byte overlong encoding

    def case_e0_9f_bf(self):
        self.run_cases(b"\xE0\x9F\xBF")  # max 3-byte overlong encoding

    def case_u0800(self):
        self.run_cases("\u0800")  # min 3-byte

    def case_u0fff(self):
        self.run_cases("\u0FFF")

    def case_u1000(self):
        self.run_cases("\u1000")

    def case_ucfff(self):
        self.run_cases("\uCFFF")

    def case_ud000(self):
        self.run_cases("\uD000")

    def case_ud7ff(self):
        self.run_cases("\uD7FF")

    def case_ed_a0_80(self):
        self.run_cases(b"\xED\xA0\x80")  # first high surrogate

    def case_ed_af_bf(self):
        self.run_cases(b"\xED\xAF\xBF")  # last high surrogate

    def case_ed_b0_80(self):
        self.run_cases(b"\xED\xB0\x80")  # first low surrogate

    def case_ed_bf_bf(self):
        self.run_cases(b"\xED\xBF\xBF")  # last low surrogate

    def case_ue000(self):
        self.run_cases("\uE000")

    def case_uffff(self):
        self.run_cases("\uFFFF")  # max 3-byte

    def case_f0_80_80_80(self):
        self.run_cases(b"\xF0\x80\x80\x80")  # min 4-byte overlong encoding

    def case_f0_bf_bf_bf(self):
        self.run_cases(b"\xF0\x8F\xBF\xBF")  # max 4-byte overlong encoding

    def case_u00010000(self):
        self.run_cases("\U00010000")  # min 4-byte

    def case_u0003ffff(self):
        self.run_cases("\U0003FFFF")

    def case_u00040000(self):
        self.run_cases("\U00040000")

    def case_u000fffff(self):
        self.run_cases("\U000FFFFF")

    def case_u00100000(self):
        self.run_cases("\U00100000")

    def case_u0010ffff(self):
        self.run_cases("\U0010FFFF")  # max 4-byte

    def case_f4_90_80_80(self):
        self.run_cases(b"\xF4\x90\x80\x80")  # first too-big encoding

    def case_f7_bf_bf_bf(self):
        self.run_cases(b"\xF7\xBF\xBF\xBF")  # max too-big 4-byte encoding

    def case_f8_x4_80(self):
        self.run_cases(b"\xF8" + b"\x80" * 4)  # min too-big 5-byte encoding

    def case_fb_x4_bf(self):
        self.run_cases(b"\xFB" + b"\xBF" * 4)  # max too-big 5-byte encoding

    def case_fc_x5_80(self):
        self.run_cases(b"\xFC" + b"\x80" * 5)  # min too-big 6-byte encoding

    def case_fd_x5_bf(self):
        self.run_cases(b"\xFD" + b"\xBF" * 5)  # max too-big 6-byte encoding

    def case_fe_x6_80(self):
        self.run_cases(b"\xFE" + b"\x80" * 6)  # min too-big 7-byte encoding

    def case_fe_x6_bf(self):
        self.run_cases(b"\xFE" + b"\xBF" * 6)  # max too-big 7-byte encoding

    def case_ff_x7_80(self):
        self.run_cases(b"\xFF" + b"\x80" * 7)  # min too-big 8-byte encoding

    def case_ff_x7_bf(self):
        self.run_cases(b"\xFF" + b"\xBF" * 7)  # max too-big 8-byte encoding

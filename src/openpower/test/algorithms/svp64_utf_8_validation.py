# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.test.common import TestAccumulatorBase
from openpower.test.state import ExpectedState
from openpower.sv.trans.svp64 import SVP64Asm


def svp64_utf8_validation_asm():
    raise NotImplementedError("not finished")
    return [
        "setvl 0, 0, 32, 0, 1, 1",  # set VL to 32
        "sv.addi *64, 0, 0",  # clear prev iter's bytes
        "loop:",
        "setvl. 0, 0, 32, 0, 1, 1",  # set VL to 32
        "sv.ori *32, *64, 0",  # copy prev iter's bytes

        # clear cur iter's bytes, so bytes beyond end end up being zeros
        "sv.addi *64, 0, 0",
        "setvl 5, 4, 32, 0, 1, 1",  # set VL to min(32, r4)
        "sv.lbz/els *64, 0(3)",  # load bytes
        "setvl 0, 0, 32, 0, 1, 1",  # set VL to 32
        # now we can operate on 32 byte chunks, branch to `fail` if they don't
        # pass validation.
        # TODO: finish
        # branch at end, so we check last bytes from prev iter first
        "bne loop",
        "li 3, 1",
        "blr",
        "fail:",
        "li 3, 0",
        "blr",
    ]


class SVP64UTF8ValidationTestCase(TestAccumulatorBase):
    def run_case(self, data):
        # type: (bytes) -> None
        expected = 1
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            expected = 0
        isa = SVP64Asm(svp64_utf8_validation_asm())
        lst = list(isa)
        initial_regs = [0x15cee3293aa9bfbe] * 128  # fill with junk
        initial_regs[3] = 0x10000  # pointer to bytes to check
        initial_regs[4] = len(data)  # length of bytes to check

        initial_mem = {}
        for i, v in enumerate(data):
            initial_mem[i + initial_regs[3]] = v, 1
        stop_at_pc = 0x10000000
        initial_sprs = {8: SelectableInt(stop_at_pc, 64)}
        e = ExpectedState(pc=stop_at_pc)
        e.intregs[3] = expected
        self.add_case(Program(lst, 0), initial_regs, initial_mem=initial_mem,
                      initial_sprs=initial_sprs, stop_at_pc=stop_at_pc,
                      expected=e)

    def run_cases(self, data):
        # type: (bytes | str) -> None
        if isinstance(data, str):
            data = data.encode("utf-8")
        data = b' ' * 8 + data + b' ' * 8
        for i in range(len(data)):
            part = data[i:]
            for j in range(len(part)):
                self.run_case(part[:j])

    def case_empty(self):
        self.run_case(b"")

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

    def case_ud800(self):
        self.run_cases("\uD800")  # surrogate

    def case_udbff(self):
        self.run_cases("\uDBFF")  # surrogate

    def case_udc00(self):
        self.run_cases("\uDC00")  # surrogate

    def case_udfff(self):
        self.run_cases("\uDFFF")  # surrogate

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

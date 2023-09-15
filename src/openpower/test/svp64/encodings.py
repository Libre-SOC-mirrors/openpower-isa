# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2023 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.test.state import ExpectedState
from openpower.test.util import assemble
from openpower.decoder.isa.caller import SVP64State
from nmutil.plain_data import plain_data
from enum import Enum
import itertools

_SCALAR_EXTRA2 = range(64)
_VECTOR_EXTRA2 = range(0, 128, 2)
_SCALAR_EXTRA3 = range(128)
_VECTOR_EXTRA3 = range(128)


@plain_data(unsafe_hash=True, frozen=True)
class _Arg:
    __slots__ = "alloc_pass",

    def __init__(self, alloc_pass):
        # type: (_AllocPass)
        self.alloc_pass = alloc_pass

    def gen(self, regs):
        raise NotImplementedError
        yield ""

    @staticmethod
    def __gen_all_args(cur_out, output, args, regs, step):
        if step >= len(args):
            output.append((cur_out.copy(), regs.copy()))
            return

        idx, arg = args[step]
        for out in arg.gen(regs):
            cur_out[idx] = out
            _Arg.__gen_all_args(cur_out, output, args, regs, step=step + 1)

    @staticmethod
    def gen_all_args(args):
        # sort by pass
        args = sorted(enumerate(args), key=lambda arg: arg[1].alloc_pass)
        output = []
        cur_out = [""] * len(args)
        _Arg.__gen_all_args(cur_out, output, args, regs={}, step=0)
        return output


_DEFAULT_TEST_VALUES = 0x123456789ABCDEF0,


@plain_data(unsafe_hash=True, frozen=True)
class _ArgReg(_Arg):
    __slots__ = "vec", "regs", "values", "all_regs"

    def __init__(self, vec, regs, values, all_regs):
        # type: (bool, range, list[int] | tuple[int, ...], bool) -> None
        self.vec = vec
        self.regs = regs
        self.values = tuple(values)
        self.all_regs = all_regs
        super().__init__(0 if all_regs else 1)

    @staticmethod
    def const(value, vec=False, regs=range(4, 32, 2)):
        # type: (int, bool, range) -> _ArgReg
        return _ArgReg(vec, regs, values=(value,), all_regs=False)

    @staticmethod
    def reg_range(vec, regs, values=_DEFAULT_TEST_VALUES, skip_r0=False):
        # type: (bool, range, list[int] | tuple[int, ...], bool) -> _ArgReg
        if skip_r0:
            assert regs.start == 0
            regs = range(regs.start + regs.step,
                         regs.stop, regs.step)
        return _ArgReg(vec, regs, values, all_regs=True)

    @staticmethod
    def s_extra2(values=_DEFAULT_TEST_VALUES, skip_r0=False):
        # type: (list[int] | tuple[int, ...], bool) -> _ArgReg
        return _ArgReg.reg_range(vec=False, regs=_SCALAR_EXTRA2,
                                 values=values, skip_r0=skip_r0)

    @staticmethod
    def v_extra2(values=_DEFAULT_TEST_VALUES, skip_r0=False):
        # type: (list[int] | tuple[int, ...], bool) -> _ArgReg
        return _ArgReg.reg_range(vec=True, regs=_VECTOR_EXTRA2,
                                 values=values, skip_r0=skip_r0)

    @staticmethod
    def s_extra3(values=_DEFAULT_TEST_VALUES, skip_r0=False):
        # type: (list[int] | tuple[int, ...], bool) -> _ArgReg
        return _ArgReg.reg_range(vec=False, regs=_SCALAR_EXTRA3,
                                 values=values, skip_r0=skip_r0)

    @staticmethod
    def v_extra3(values=_DEFAULT_TEST_VALUES, skip_r0=False):
        # type: (list[int] | tuple[int, ...], bool) -> _ArgReg
        return _ArgReg.reg_range(vec=True, regs=_VECTOR_EXTRA3,
                                 values=values, skip_r0=skip_r0)

    def gen(self, regs):
        for reg in self.regs:
            if reg in regs:
                continue
            regs[reg] = self.values
            s = str(reg)
            if self.vec:
                s = "*" + s
            yield (reg, s)
            del regs[reg]
            if not self.all_regs:
                break


@plain_data(unsafe_hash=True, frozen=True)
class _ArgLiteral(_Arg):
    __slots__ = "text",

    def __init__(self, text):
        # type: (str) -> None
        self.text = text
        super().__init__(0)

    def gen(self, regs):
        yield (None, self.text)


class SVP64EncodingsCases(TestAccumulatorBase):
    def do_check(self, insn, args, gen_expected, src_loc_at=0):
        UNINIT = int.from_bytes(b"uninit..", "little")
        all_args = _Arg.gen_all_args(args)
        for cur_args, cur_regs in all_args:
            asm = insn + " " + ", ".join(map(lambda v: v[1], cur_args))
            with self.subTest(asm=asm):
                prog = assemble([asm])
                for values in itertools.product(*cur_regs.values()):
                    gprs = [UNINIT] * 128
                    for reg, v in zip(cur_regs.keys(), values):
                        gprs[reg] = v
                    svstate = SVP64State()
                    svstate.vl = 1
                    svstate.maxvl = 1
                    e = gen_expected(cur_args, gprs)
                    expected_gprs = []
                    input_gprs = []
                    for reg in sorted(cur_regs.keys()):
                        iv = gprs[reg]
                        ev = e.intregs[reg]
                        input_gprs.append(f"r{reg} = 0x{iv:X}")
                        expected_gprs.append(f"r{reg} = 0x{ev:X}")
                    expected_gprs = "\n".join(expected_gprs)
                    input_gprs = "\n".join(input_gprs)
                    with self.subTest(
                        expected_gprs=expected_gprs, input_gprs=input_gprs,
                    ):
                        self.add_case(prog, gprs, expected=e,
                                      initial_svstate=svstate,
                                      src_loc_at=src_loc_at + 1)

    # test RM-1P-2S1D

    @staticmethod
    def __sv_add_gen_expected(cur_args, gprs):
        e = ExpectedState(pc=8, int_regs=gprs)
        RT_reg = cur_args[0][0]
        RA_reg = cur_args[1][0]
        RB_reg = cur_args[2][0]
        RA = gprs[RA_reg]
        RB = gprs[RB_reg]
        e.intregs[RT_reg] = (RA + RB) % 2 ** 64
        return e

    def case_sv_add_vvs_rt(self):
        self.do_check("sv.add", [
            _ArgReg.v_extra3(),
            _ArgReg.const(1, vec=True),
            _ArgReg.const(1)], self.__sv_add_gen_expected)

    def case_sv_add_vvs_ra(self):
        self.do_check("sv.add", [
            _ArgReg.const(0, vec=True),
            _ArgReg.v_extra3(),
            _ArgReg.const(1)], self.__sv_add_gen_expected)

    def case_sv_add_vvs_rb(self):
        self.do_check("sv.add", [
            _ArgReg.const(0, vec=True),
            _ArgReg.const(1, vec=True),
            _ArgReg.s_extra3()], self.__sv_add_gen_expected)

    # test RM-1P-3S1D

    @staticmethod
    def __sv_maddedu_gen_expected(cur_args, gprs):
        e = ExpectedState(pc=8, int_regs=gprs)
        RT_reg = cur_args[0][0]
        RA_reg = cur_args[1][0]
        RB_reg = cur_args[2][0]
        RC_reg = cur_args[3][0]
        RA = gprs[RA_reg]
        RB = gprs[RB_reg]
        RC = gprs[RC_reg]
        v = (RA * RB) + RC
        RT = v % 2 ** 64
        RS = v >> 64  # can't overflow, so no need for wrapping
        e.intregs[RT_reg] = RT
        e.intregs[RC_reg] = RS
        return e

    def case_sv_maddedu_vvss_rt(self):
        self.do_check("sv.maddedu", [
            _ArgReg.v_extra2(),
            _ArgReg.const(1, vec=True),
            _ArgReg.const(1),
            _ArgReg.const(0)], self.__sv_maddedu_gen_expected)

    def case_sv_maddedu_vvss_ra(self):
        self.do_check("sv.maddedu", [
            _ArgReg.const(0, vec=True),
            _ArgReg.v_extra2(),
            _ArgReg.const(1),
            _ArgReg.const(0)], self.__sv_maddedu_gen_expected)

    def case_sv_maddedu_vvss_rb(self):
        self.do_check("sv.maddedu", [
            _ArgReg.const(0, vec=True),
            _ArgReg.const(1, vec=True),
            _ArgReg.s_extra2(),
            _ArgReg.const(0)], self.__sv_maddedu_gen_expected)

    def case_sv_maddedu_vvss_rc(self):
        self.do_check("sv.maddedu", [
            _ArgReg.const(0, vec=True),
            _ArgReg.const(0, vec=True),
            _ArgReg.const(0),
            _ArgReg.s_extra2()], self.__sv_maddedu_gen_expected)

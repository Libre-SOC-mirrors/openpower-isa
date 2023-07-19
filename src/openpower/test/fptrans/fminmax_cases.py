from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.insndb.asm import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.power_enums import FMinMaxMode
from openpower.fpscr import FPSCRState
import operator
import struct
import itertools


_TEST_VALUES = [
    0x0000_0000_0000_0000,  # 0.0
    0x8000_0000_0000_0000,  # -0.0
    # too many values, comment some out
    # 0x0000_0000_0000_0001,  # min denormal
    # 0x8000_0000_0000_0001,  # - min denormal
    # 0x0010_0000_0000_0000,  # min normal
    # 0x8010_0000_0000_0000,  # - min normal
    # 0x36A0_0000_0000_0000,  # min f32 denormal
    # 0xB6A0_0000_0000_0000,  # - min f32 denormal
    # 0x3810_0000_0000_0000,  # min f32 normal
    # 0xB810_0000_0000_0000,  # - min f32 normal
    0x3FF0_0000_0000_0000,  # 1.0
    0xBFF0_0000_0000_0000,  # -1.0
    0x4000_0000_0000_0000,  # 2.0
    0xC000_0000_0000_0000,  # -2.0
    # 0x47EF_FFFF_E000_0000,  # max f32 normal
    # 0xC7EF_FFFF_E000_0000,  # - max f32 normal
    # 0x7FEF_FFFF_FFFF_FFFF,  # max normal
    # 0xFFEF_FFFF_FFFF_FFFF,  # - max normal
    0x7FF0_0000_0000_0000,  # infinity
    0xFFF0_0000_0000_0000,  # -infinity
    # 0x7FF0_0000_0000_0001,  # first sNaN
    0xFFF0_0000_0000_0001,  # - first sNaN
    # 0x7FF0_0000_2000_0000,  # first f32 sNaN
    # 0xFFF0_0000_2000_0000,  # - first f32 sNaN
    # 0x7FF7_FFFF_E000_0000,  # last f32 sNaN
    # 0xFFF7_FFFF_E000_0000,  # - last f32 sNaN
    # 0x7FF7_FFFF_FFFF_FFFF,  # last sNaN
    # 0xFFF7_FFFF_FFFF_FFFF,  # - last sNaN
    0x7FF8_0000_0000_0000,  # first qNaN
    # 0xFFF8_0000_0000_0000,  # - first qNaN
    # 0x7FFF_FFFF_E000_0000,  # last f32 qNaN
    # 0xFFFF_FFFF_E000_0000,  # - last f32 qNaN
    # 0x7FFF_FFFF_FFFF_FFFF,  # last qNaN
    0xFFFF_FFFF_FFFF_FFFF,  # - last qNaN
]


class FMinMaxCases(TestAccumulatorBase):
    # _FILTER is for debugging
    _FILTER = None
    # _FILTER = {
    #     'RA': '0x0', 'RB': '0x0',
    #     'FMM': 'FMinMaxMode.fminnum08', 'VE': False, 'initial_VXSNAN': False,
    #     'expected': '0x0', 'any_snan': False, 'CR1': 0,
    # }

    def reference_fminmax(self, FMM, RA, RB):
        # type: (FMinMaxMode, int, int) -> tuple[int, bool]
        op = FMinMaxMode(FMM.value & 0b11)
        is_max = bool(FMM.value & 0b1000)
        is_mag = bool(FMM.value & 0b100)
        MANT_MASK = 0xF_FFFF_FFFF_FFFF
        EXP_MASK = 0x7FF0_0000_0000_0000
        SIGN_MASK = 0x8000_0000_0000_0000
        a_is_nan = RA & MANT_MASK and RA & EXP_MASK == EXP_MASK
        a_quieted = RA | 0x8_0000_0000_0000
        b_is_nan = RB & MANT_MASK and RB & EXP_MASK == EXP_MASK
        b_quieted = RB | 0x8_0000_0000_0000
        a_is_snan = a_is_nan and a_quieted != RA
        b_is_snan = b_is_nan and b_quieted != RB
        any_snan = a_is_snan or b_is_snan
        if op is FMinMaxMode.fminnum08:
            if a_is_snan:
                return a_quieted, any_snan
            if b_is_snan:
                return b_quieted, any_snan
            if a_is_nan and b_is_nan:
                return a_quieted, any_snan
            if a_is_nan:
                return RB, any_snan
            if b_is_nan:
                return RA, any_snan
        elif op is FMinMaxMode.fmin19:
            if a_is_nan:
                return a_quieted, any_snan
            if b_is_nan:
                return b_quieted, any_snan
        elif op is FMinMaxMode.fminnum19:
            if a_is_nan and b_is_nan:
                return a_quieted, any_snan
            if a_is_nan:
                return RB, any_snan
            if b_is_nan:
                return RA, any_snan
        else:
            assert op is FMinMaxMode.fminc
            if a_is_nan or b_is_nan:
                return RB, any_snan
            if RA & ~SIGN_MASK == 0 and RB & ~SIGN_MASK == 0:
                return RB, any_snan
        if RA & ~SIGN_MASK == 0 and RB & ~SIGN_MASK == 0:
            if is_max:
                return RA & RB, any_snan
            return RA | RB, any_snan
        cmp = operator.lt
        if is_max:
            cmp = operator.gt
        cmp_RA = RA
        cmp_RB = RB
        if is_mag and RA & ~SIGN_MASK != RB & ~SIGN_MASK:
            cmp_RA &= ~SIGN_MASK
            cmp_RB &= ~SIGN_MASK
        cmp_RA = struct.unpack("<d", struct.pack("<Q", cmp_RA))[0]
        cmp_RB = struct.unpack("<d", struct.pack("<Q", cmp_RB))[0]
        if cmp(cmp_RA, cmp_RB):
            return RA, any_snan
        return RB, any_snan

    def fminmax(self, FMM, VE, initial_VXSNAN):
        # type: (FMinMaxMode, bool, bool) -> None
        if self._FILTER is not None and (
                str(FMM) != self._FILTER['FMM'] or
                VE != self._FILTER['VE'] or
                initial_VXSNAN != self._FILTER['initial_VXSNAN']):
            return
        prog = Program(list(SVP64Asm([f"fminmax. 3,4,5,{FMM.value}"])), False)
        for RA in _TEST_VALUES:
            for RB in _TEST_VALUES:
                gprs = [0] * 32
                fprs = [0] * 32
                fprs[3] = 0x0123_4567_89AB_CDEF
                fprs[4] = RA
                fprs[5] = RB
                e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
                initial_fpscr = FPSCRState()
                initial_fpscr.VE = VE
                initial_fpscr.VXSNAN = initial_VXSNAN
                fpscr = FPSCRState(initial_fpscr)
                RT, any_snan = self.reference_fminmax(FMM, RA, RB)
                if any_snan:
                    if not fpscr.VXSNAN:
                        fpscr.FX = 1
                    fpscr.VXSNAN = 1
                if not fpscr.VE or not any_snan:
                    e.fpregs[3] = RT
                else:
                    e.pc = 0x700
                    e.sprs['SRR0'] = 0  # insn is at address 0
                    e.sprs['SRR1'] = e.msr | (1 << (63 - 43))
                    e.msr = 0x9000000000000001
                e.fpscr = int(fpscr)
                cr1 = int(fpscr.FX) << 3
                cr1 |= int(fpscr.FEX) << 2
                cr1 |= int(fpscr.VX) << 1
                cr1 |= int(fpscr.OX)
                e.crregs[1] = cr1
                kwargs = dict(
                    RA=hex(RA), RB=hex(RB), FMM=str(FMM), VE=VE,
                    initial_VXSNAN=initial_VXSNAN, expected=hex(RT),
                    any_snan=any_snan, CR1=cr1)
                if self._FILTER is not None and kwargs != self._FILTER:
                    continue
                with self.subTest(**kwargs):
                    self.add_case(prog, gprs, fpregs=fprs, expected=e,
                                  initial_fpscr=int(initial_fpscr))

    def case_fminmax(self):
        for FMM, VE, VXSNAN in itertools.product(
                FMinMaxMode, (False, True), (False, True)):
            if VE and VXSNAN:
                # isn't really a legal state that the simulator can end up in
                # since MSR.FE0/FE1 are also set, this would have been caught
                # by whatever previous instruction changed to this state
                continue
            self.fminmax(FMM, VE, VXSNAN)

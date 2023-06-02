import unittest
from copy import deepcopy

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.isa.caller import CRFields, SVP64State
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.insndb.asm import SVP64Asm


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        print("GPR")
        sim.gpr.dump()
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_1_setvl_zero_rc1(self):
        lst = SVP64Asm(["setvl. 5, 4, 5, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, MAXVL=5) which is going to get erased by setvl
        # but, ha! r4 (RA) is zero. and Rc=1. therefore, CR0 should be set EQ
        svstate = SVP64State()
        svstate.maxvl = 5  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 0)
            self.assertEqual(sim.svstate.maxvl, 5)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            self.assertEqual(sim.svstate.vfirst, 0)
            print("      gpr4", sim.gpr(4))
            self.assertEqual(sim.gpr(4), SelectableInt(0, 64))
            print("      gpr5", sim.gpr(5))
            self.assertEqual(sim.gpr(5), SelectableInt(0, 64))
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 1)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_2_setvl_nonzero_rc1(self):
        lst = SVP64Asm(["setvl. 5, 4, 5, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, MAXVL=5) which is going to get erased by setvl
        # r4 (RA) is 4. and Rc=1. therefore, CR0 should be set to GT
        svstate = SVP64State()
        svstate.maxvl = 5  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        initial_regs = [0] * 32
        initial_regs[4] = 4

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_regs=initial_regs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 4)
            self.assertEqual(sim.svstate.maxvl, 5)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            self.assertEqual(sim.svstate.vfirst, 0)
            print("      gpr4", sim.gpr(4))
            self.assertEqual(sim.gpr(4), SelectableInt(4, 64))
            print("      gpr5", sim.gpr(5))
            self.assertEqual(sim.gpr(5), SelectableInt(4, 64))
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_3_setvl_overflow_rc1(self):
        lst = SVP64Asm(["setvl. 5, 4, 5, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, MAXVL=5) which is going to get erased by setvl
        # r4 (RA) is 4. and Rc=1. therefore, CR0 should be set to GT
        svstate = SVP64State()
        svstate.maxvl = 5  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        initial_regs = [0] * 32
        initial_regs[4] = 1000  # much greater than MAXVL

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_regs=initial_regs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 5)
            self.assertEqual(sim.svstate.maxvl, 5)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            self.assertEqual(sim.svstate.vfirst, 0)
            print("      gpr4", sim.gpr(4))
            self.assertEqual(sim.gpr(4), SelectableInt(1000, 64))  # unmodified
            print("      gpr5", sim.gpr(5))
            self.assertEqual(sim.gpr(5), SelectableInt(5, 64)
                             )  # equal to MAXVL
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 1)

    def test_4_setvl_max_overflow_rc1(self):
        """this should set overflow even though VL gets set to MAXVL
        at its limit of 127 (0b1111111)
        """
        lst = SVP64Asm(["setvl. 5, 4, 127, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, MAXVL=5) which is going to get erased by setvl
        # r4 (RA) is 4. and Rc=1. therefore, CR0 should be set to GT
        svstate = SVP64State()
        svstate.maxvl = 5  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        initial_regs = [0] * 32
        initial_regs[4] = 1000  # much greater than MAXVL

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_regs=initial_regs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 127)
            self.assertEqual(sim.svstate.maxvl, 127)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            self.assertEqual(sim.svstate.vfirst, 0)
            print("      gpr4", sim.gpr(4))
            self.assertEqual(sim.gpr(4), SelectableInt(1000, 64))  # unmodified
            print("      gpr5", sim.gpr(5))
            self.assertEqual(sim.gpr(5), SelectableInt(127, 64))  # eq. MAXVL
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 1)

    def test_5_setvl_max_rc1(self):
        """this should not set when VL gets set to MAXVL
        at its limit of 127 (0b1111111)
        """
        lst = SVP64Asm(["setvl. 5, 4, 127, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, MAXVL=5) which is going to get erased by setvl
        # r4 (RA) is 4. and Rc=1. therefore, CR0 should be set to GT
        svstate = SVP64State()
        svstate.maxvl = 5  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        initial_regs = [0] * 32
        initial_regs[4] = 127  # exactly equal to MAXVL

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_regs=initial_regs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 127)
            self.assertEqual(sim.svstate.maxvl, 127)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            self.assertEqual(sim.svstate.vfirst, 0)
            print("      gpr4", sim.gpr(4))
            self.assertEqual(sim.gpr(4), SelectableInt(127, 64))  # unmodified
            print("      gpr5", sim.gpr(5))
            self.assertEqual(sim.gpr(5), SelectableInt(127, 64))  # eq. MAXVL
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_5_setvl_rt0_rc1(self):
        """odd one. Rc=1, RT=0, RA!=0, so RT does not get set, but VL does.
        confirms that when Rc=1 and RT is unmodified that CR0 still is updated
        """
        lst = SVP64Asm(["setvl. 0, 4, 5, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, MAXVL=5) which is going to get erased by setvl
        # r4 (RA) is 4. and Rc=1. therefore, CR0 should be set to GT
        svstate = SVP64State()
        svstate.maxvl = 5  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        initial_regs = [0] * 32
        initial_regs[4] = 127  # overlimit, should set CR0.SO=1, and CR0.GT=1

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_regs=initial_regs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 5)
            self.assertEqual(sim.svstate.maxvl, 5)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            self.assertEqual(sim.svstate.vfirst, 0)
            print("      gpr0", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))  # unmodified
            print("      gpr4", sim.gpr(4))
            self.assertEqual(sim.gpr(4), SelectableInt(127, 64))  # unmodified
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 1)

    def test_sv_sv_setvl(self):
        """test sv.setvl instruction works.  WARNING, going beyond
        RT=0..31 does not work, bug in PowerDecoder2 / ISACaller,
        related to RT_OR_ZERO and to simplev.mdwn pseudocode having
        _RT not be EXTRA-extended properly
        """
        lst = SVP64Asm(["sv.setvl 8, 31, 10, 0, 1, 1",  # setvl into RT=8
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=4) which is going to get erased by setvl
        svstate = SVP64State()
        svstate.vl = 4  # VL
        svstate.maxvl = 4  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        initial_regs = [0] * 64
        initial_regs[31] = 200

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=initial_regs,
                                       svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 10)
            self.assertEqual(sim.svstate.maxvl, 10)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            self.assertEqual(sim.svstate.vfirst, 0)
            print("      gpr31", sim.gpr(31))
            print("      gpr8", sim.gpr(8))
            self.assertEqual(sim.gpr(8), SelectableInt(10, 64))

    def test_svstep_1(self):
        lst = SVP64Asm(["setvl 0, 0, 10, 1, 1, 1",  # actual setvl (VF mode)
                        "svstep 0, 1, 0",  # svstep
                        "svstep 0, 1, 0",  # svstep
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=4) which is going to get erased by setvl
        svstate = SVP64State()
        svstate.vl = 4  # VL
        svstate.maxvl = 4  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 10)
            self.assertEqual(sim.svstate.maxvl, 10)
            self.assertEqual(sim.svstate.srcstep, 2)
            self.assertEqual(sim.svstate.dststep, 2)
            self.assertEqual(sim.svstate.vfirst, 1)
            print("      gpr1", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))

    def test_svstep_2(self):
        """tests svstep when it reaches VL
        """
        lst = SVP64Asm(["setvl 0, 0, 2, 1, 1, 1",  # actual setvl (VF mode)
                        "svstep. 0, 1, 0",  # svstep (Rc=1)
                        "svstep. 0, 1, 0",  # svstep (Rc=1)
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 2)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            # when end reached, vertical mode is exited
            self.assertEqual(sim.svstate.vfirst, 0)
            print("      gpr1", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

    def test_svstep_3(self):
        """tests svstep when it *doesn't* reach VL
        """
        lst = SVP64Asm(["setvl 0, 0, 3, 1, 1, 1",  # actual setvl (VF mode)
                        "svstep. 0, 1, 0",  # svstep (Rc=1)
                        "svstep. 0, 1, 0",  # svstep (Rc=1)
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 3)
            self.assertEqual(sim.svstate.maxvl, 3)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep, 2)
            self.assertEqual(sim.svstate.dststep, 2)
            print("      gpr1", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            self.assertEqual(sim.svstate.vfirst, 1)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_setvl_ctr_1_rc1(self):
        """setvl CTR mode, with Rc=1, testing if VL and MVL are over-ridden
        and CR0 set correctly
        """
        lst = SVP64Asm(["setvl. 1, 0, 10, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2), want to see if these get changed
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        sprs = {'CTR': 5,
                }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_sprs=sprs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            self.assertEqual(sim.svstate.vl, 5)
            self.assertEqual(sim.svstate.maxvl, 10)
            print("      gpr1", sim.gpr(1))
            self.assertEqual(sim.gpr(1), SelectableInt(5, 64))

            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_setvl_ctr_1(self):
        """setvl CTR mode, testing if VL and MVL are over-ridden
        """
        lst = SVP64Asm(["setvl 1, 0, 10, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2), want to see if these get changed
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        sprs = {'CTR': 5,
                }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_sprs=sprs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            self.assertEqual(sim.svstate.vl, 5)
            self.assertEqual(sim.svstate.maxvl, 10)
            print("      gpr1", sim.gpr(1))
            self.assertEqual(sim.gpr(1), SelectableInt(5, 64))

            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_setvl_ctr_2_rc1(self):
        """setvl Rc=1, CTR large, testing if VL and MVL are over-ridden,
        check if CR0.SO gets set
        """
        lst = SVP64Asm(["setvl. 1, 0, 10, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2), want to see if these get changed
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        sprs = {'CTR': 0x1000000000,
                }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_sprs=sprs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            self.assertEqual(sim.svstate.vl, 10)
            self.assertEqual(sim.svstate.maxvl, 10)
            print("      gpr1", sim.gpr(1))
            self.assertEqual(sim.gpr(1), SelectableInt(10, 64))

            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 1)

    def test_setvl_ctr_2(self):
        """setvl CTR large, testing if VL and MVL are over-ridden
        """
        lst = SVP64Asm(["setvl 1, 0, 10, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2), want to see if these get changed
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        sprs = {'CTR': 0x1000000000,
                }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_sprs=sprs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            self.assertEqual(sim.svstate.vl, 10)
            self.assertEqual(sim.svstate.maxvl, 10)
            print("      gpr1", sim.gpr(1))
            self.assertEqual(sim.gpr(1), SelectableInt(10, 64))

    def test_setvl_1(self):
        """straight setvl, testing if VL and MVL are over-ridden
        """
        lst = SVP64Asm(["setvl 0, 0, 10, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2), want to see if these get changed
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            self.assertEqual(sim.svstate.vl, 10)
            self.assertEqual(sim.svstate.maxvl, 10)
            print("      gpr1", sim.gpr(1))
            self.assertEqual(sim.gpr(1), SelectableInt(0, 64))

    def test_setvl_2(self):
        """setvl, testing if VL is transferred to RT, and MVL truncates it
        """
        lst = SVP64Asm(["setvl 1, 0, 2, 0, 0, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2), want to see if these get changed
        svstate = SVP64State()
        svstate.vl = 10  # VL
        svstate.maxvl = 10  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            self.assertEqual(sim.svstate.maxvl, 2)
            self.assertEqual(sim.svstate.vl, 2)
            print("      gpr1", sim.gpr(1))
            self.assertEqual(sim.gpr(1), SelectableInt(2, 64))

    def test_svstep_inner_loop_6(self):
        """tests svstep inner loop, running 6 times, looking for "k".
        also sees if k is actually output into reg 2 (RT=2)
        """
        lst = SVP64Asm([
            # set triple butterfly mode with persistent "REMAP"
            "svshape 8, 1, 1, 1, 1",
            "svremap 31, 1, 0, 2, 0, 1, 1",
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 2, 2, 0",  # svstep (Rc=1)
        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        # svstate.vl = 2 # VL
        # svstate.maxvl = 2 # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 12)
            self.assertEqual(sim.svstate.maxvl, 12)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep, 6)
            self.assertEqual(sim.svstate.dststep, 6)
            self.assertEqual(sim.gpr(2), SelectableInt(1, 64))
            self.assertEqual(sim.svstate.vfirst, 1)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 1)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_svstep_inner_loop_3(self):
        """tests svstep inner loop, running 3 times
        """
        lst = SVP64Asm([
            # set triple butterfly mode with persistent "REMAP"
            "svshape 8, 1, 1, 1, 1",
            "svremap 31, 1, 0, 2, 0, 1, 1",
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        # svstate.vl = 2 # VL
        # svstate.maxvl = 2 # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 12)
            self.assertEqual(sim.svstate.maxvl, 12)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep, 3)
            self.assertEqual(sim.svstate.dststep, 3)
            self.assertEqual(sim.gpr(0), SelectableInt(4, 64))
            self.assertEqual(sim.svstate.vfirst, 1)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 1)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_svstep_inner_loop_4(self):
        """tests svstep inner loop, running 4 times
        """
        lst = SVP64Asm([
            # set triple butterfly mode with persistent "REMAP"
            "svshape 8, 1, 1, 1, 1",
            "svremap 31, 1, 0, 2, 0, 1, 1",
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        # svstate.vl = 2 # VL
        # svstate.maxvl = 2 # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 12)
            self.assertEqual(sim.svstate.maxvl, 12)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep, 4)
            self.assertEqual(sim.svstate.dststep, 4)
            self.assertEqual(sim.gpr(0), SelectableInt(6, 64))
            self.assertEqual(sim.svstate.vfirst, 1)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 1)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_svstep_inner_loop_4_jl(self):
        """tests svstep inner loop, running 4 times, checking
           "jl" is returned after 4th iteration
        """
        lst = SVP64Asm([
            # set triple butterfly mode with persistent "REMAP"
            "svshape 8, 1, 1, 1, 1",
            "svremap 31, 1, 0, 2, 0, 1, 1",
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 0, 2, 0",  # svstep (Rc=1)
            "svstep. 2, 2, 0",  # svstep (Rc=1)
        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        # svstate.vl = 2 # VL
        # svstate.maxvl = 2 # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 12)
            self.assertEqual(sim.svstate.maxvl, 12)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep, 4)
            self.assertEqual(sim.svstate.dststep, 4)
            self.assertEqual(sim.gpr(2), SelectableInt(6, 64))
            self.assertEqual(sim.svstate.vfirst, 1)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 1)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_svstep_inner_loop_8_jl(self):
        """tests svstep inner loop, running 8 times (sv.setvl.), checking
            jl is copied into a *Vector* result.

            fuuun...
        """

        # below, the indices (done manually here, sigh)o
        # really they should be generated by the radix_dct_yield.py
        # program
        j_h = [0, 2, 4, 6, 0, 1, 4, 5, 0, 1, 2, 3]
        k_e = [0, 0, 0, 0, 0, 2, 0, 2, 0, 1, 2, 3]

        lst = SVP64Asm([
            # set FFT triple butterfly mode with persistent "REMAP"
            "svshape 8, 1, 1, 1, 0",
            "svremap 0, 0, 0, 2, 0, 1, 1",
            "sv.svstep *0, 1, 1",  # svstep get vector of j+halfsize
            "sv.svstep *16, 3, 1",  # svstep get vector of k in exptable[k]
        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        # svstate.vl = 2 # VL
        # svstate.maxvl = 2 # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 12)
            self.assertEqual(sim.svstate.maxvl, 12)
            # svstep called four times, reset occurs, srcstep zero
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            for i in range(12):
                self.assertEqual(sim.gpr(0+i), SelectableInt(j_h[i], 64))
                self.assertEqual(sim.gpr(16+i), SelectableInt(k_e[i], 64))
            self.assertEqual(sim.svstate.vfirst, 0)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_sv_add(self):
        """sets VL=2 then adds:
           * 1 = 5 + 9   => 0x5555 = 0x4321+0x1234
           * 2 = 6 + 10  => 0x3334 = 0x2223+0x1111
        """
        isa = SVP64Asm(["setvl 0, 0, 2, 0, 1, 1",
                        'sv.add *1, *5, *9',
                        "setvl 3, 0, 1, 0, 0, 0",
                        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = 0x5555
        expected_regs[2] = 0x3334
        expected_regs[3] = 2       # setvl places copy of VL here

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self._check_regs(sim, expected_regs)

    def test_svstep_add_1(self):
        """tests svstep with an add, when it reaches VL
        lst = SVP64Asm(["setvl 0, 0, 2, 1, 1, 1",
                        'sv.add *1, *5, *9',
                        "svstep. 0, 1, 0", # svstep (Rc=1)
                        "setvl. 0, 0, 1, 1, 0, 0",
                        'sv.add *1, *5, *9',
                        "svstep. 3, 1, 0", # svstep (Rc=1)
                        "setvl 4, 0, 1, 0, 0, 0", # getvl
                        ])
        sequence is as follows:
        * setvl sets VL=2 but also "Vertical First" mode.
          this sets SVSTATE[SVF].
        * first add, which has srcstep/dststep = 0, does add 1,5,9
        * svstep EXPLICITLY walks srcstep/dststep to next element
        * second add, which now has srcstep/dststep = 1, does add 2,6,10
        * svstep EXPLICITLY walks srcstep/dststep to next element,
          which now equals VL.  srcstep and dststep are both set to
          zero
        """
        lst = SVP64Asm(["setvl 0, 0, 2, 1, 1, 1",
                        'sv.add *1, *5, *9',
                        "svstep. 0, 1, 0",  # svstep (Rc=1)
                        'sv.add *1, *5, *9',
                        "svstep. 3, 1, 0",  # svstep (Rc=1)
                        "setvl 4, 0, 1, 0, 0, 0",  # getvl
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = 0x5555
        expected_regs[2] = 0x3334
        expected_regs[4] = 2       # setvl places copy of VL here

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 2)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            # when end reached, vertical mode is exited
            self.assertEqual(sim.svstate.vfirst, 0)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

            # check registers as expected
            self._check_regs(sim, expected_regs)

    def test_svstep_add_2(self):
        """tests svstep with a branch.
        lst = SVP64Asm(["setvl 0, 0, 2, 1, 1, 1",
                        'sv.add *1, *5, *9',
                        "svstep. 0, 1, 0", # svstep (Rc=1)
                        "bc 6, 3, -0xc"
                        ])
        sequence is as follows:
        * setvl sets VL=2 but also "Vertical First" mode.
          this sets MSR[SVF].
        * first time add, which has srcstep/dststep = 0, does add 1,5,9
        * svstep EXPLICITLY walks srcstep/dststep to next element,
          not yet met VL, so CR0.EQ is set to zero
        * branch conditional checks bne on CR0, jumps back TWELVE bytes
          because whilst branch is 32-bit the sv.add is 64-bit
        * second time add, which now has srcstep/dststep = 1, does add 2,6,10
        * svstep walks to next element, meets VL, so:
          - srcstep and dststep set to zero
          - CR0.EQ set to one
          - MSR[SVF] is cleared
        * branch conditional detects CR0.EQ=1 and FAILs the condition,
          therefore loop ends.

        we therefore have an explicit "Vertical-First" system which can
        have **MULTIPLE* instructions inside a loop, running each element 0
        first, then looping back and running all element 1, then all element 2
        etc.
        """
        lst = SVP64Asm(["setvl 0, 0, 2, 1, 1, 1",
                        'sv.add *1, *5, *9',
                        "svstep. 0, 1, 0",  # svstep (Rc=1)
                        "bc 6, 3, -0xc"  # branch to add (64-bit op so -0xc!)
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = 0x5555
        expected_regs[2] = 0x3334

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 2)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            # when end reached, vertical mode is exited
            self.assertEqual(sim.svstate.vfirst, 0)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

            # check registers as expected
            self._check_regs(sim, expected_regs)

    def test_svstep_max_idx(self):
        """tests svstep with a branch, get the index of the greatest element.
        uses sv.cmp and sv.isel as a temporary substitute for sv.max,
        but also uses the same trick when getting the srcstep.
        """
        lst = SVP64Asm(["setvl 0, 0, 5, 1, 1, 1",
                        'sv.cmp 0, 1, *4, 14',  # r8 contains the temp
                        'sv.isel 14,*4,14,1',  # copy if cmp was greater
                        "svstep. 12, 6, 0",  # get srcstep
                        'sv.isel 10,12,10,1',  # copy if cmp was greater
                        "svstep. 0, 1, 0",  # svstep (Rc=1)
                        "bc 6, 3, -0x24"  # branch to cmp
                        ])
        lst = list(lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[4] = 0x2
        initial_regs[5] = 0x1
        initial_regs[6] = 0x7
        initial_regs[7] = 0x9
        initial_regs[8] = 0x3

        # copy before running
        expected_regs = deepcopy(initial_regs)
        idx = -1
        maxval = -1
        for i in range(5):
            if initial_regs[4+i] > maxval:
                maxval = initial_regs[4+i]
                idx = i
        expected_regs[14] = maxval  # largest number
        expected_regs[12] = idx     # index of largest

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 5)
            self.assertEqual(sim.svstate.maxvl, 5)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            # when end reached, vertical mode is exited
            self.assertEqual(sim.svstate.vfirst, 0)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

            # check registers as expected
            self._check_regs(sim, expected_regs)

    def test_svremap(self):
        """svremap, see if values get set
        """
        lst = SVP64Asm(["svremap 11, 0, 1, 2, 3, 3, 1",
                        ])
        lst = list(lst)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program)
            svstate = sim.svstate
            print("SVREMAP after", bin(svstate.value))
            print("        men", bin(svstate.SVme))
            print("        mi0", bin(svstate.mi0))
            print("        mi1", bin(svstate.mi1))
            print("        mi2", bin(svstate.mi2))
            print("        mo0", bin(svstate.mo0))
            print("        mo1", bin(svstate.mo1))
            print("    persist", bin(svstate.RMpst))
            self.assertEqual(svstate.SVme, 11)
            self.assertEqual(svstate.mi0, 0)
            self.assertEqual(svstate.mi1, 1)
            self.assertEqual(svstate.mi2, 2)
            self.assertEqual(svstate.mo0, 3)
            self.assertEqual(svstate.mo1, 3)
            self.assertEqual(svstate.RMpst, 1)

    def test_svstep_iota(self):
        """tests svstep "straight", placing srcstep, dststep into vector
        """
        lst = SVP64Asm(["setvl 0, 0, 4, 0, 1, 1",
                        "sv.svstep *0, 5, 1",  # svstep get vector srcstep
                        "sv.svstep. *4, 6, 1",  # svstep get vector dststep
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        # svstate.vl = 2 # VL
        # svstate.maxvl = 2 # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 4)
            self.assertEqual(sim.svstate.maxvl, 4)
            # svstep called four times, reset occurs, srcstep zero
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            for i in range(4):
                self.assertEqual(sim.gpr(0+i), SelectableInt(i, 64))
                self.assertEqual(sim.gpr(4+i), SelectableInt(i, 64))
            self.assertEqual(sim.svstate.vfirst, 0)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

    def test_svstep_iota_mask(self):
        """tests svstep "straight", placing srcstep, dststep into vector
        """
        lst = SVP64Asm(["setvl 0, 0, 5, 0, 1, 1",
                        "sv.svstep/m=r30 *0, 5, 1",  # svstep get vector srcstep
                        "sv.svstep./m=r30 *8, 6, 1", # svstep get vector dststep
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        # svstate.vl = 2 # VL
        # svstate.maxvl = 2 # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        mask = 0b10101
        initial_regs = [0] * 32
        initial_regs[30] = mask

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_regs=initial_regs)
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 5)
            self.assertEqual(sim.svstate.maxvl, 5)
            # svstep called four times, reset occurs, srcstep zero
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            sim.gpr.dump()
            for i in range(5):
                if mask & (1 << i):
                    tst = i
                else:
                    tst = 0
                self.assertEqual(sim.gpr(0+i), SelectableInt(tst, 64))
                self.assertEqual(sim.gpr(8+i), SelectableInt(tst, 64))
            self.assertEqual(sim.svstate.vfirst, 0)
            CR4 = sim.crl[4]
            print("      CR4", bin(CR4.get_range().value))
            self.assertEqual(CR4[CRFields.EQ], 0)
            self.assertEqual(CR4[CRFields.LT], 0)
            self.assertEqual(CR4[CRFields.GT], 0)
            self.assertEqual(CR4[CRFields.SO], 0)

    def run_tst_program(self, prog, initial_regs=None,
                        svstate=None,
                        initial_sprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate,
                            initial_sprs=initial_sprs)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()

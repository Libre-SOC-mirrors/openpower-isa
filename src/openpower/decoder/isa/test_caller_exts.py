import codecs
import csv
import glob
import os
import re
import unittest

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.isa.test_runner import run_tst
from openpower.decoder.power_decoder import create_pdecode
from openpower.decoder.power_decoder2 import PowerDecode2
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program


def tstgen(mapping):
    zeros = [0] * 32
    for chunk in (mapping[idx:idx+32] for idx in range(0, len(mapping), 32)):
        instrs = []
        iregs = []
        oregs = []
        for (idx, (instr, ireg, oreg)) in enumerate(chunk):
            instrs.append(f"{instr} {idx}, {idx}")
            iregs.append(ireg)
            oregs.append(oreg)
        iregs = (iregs + zeros)[:32]
        oregs = (oregs + zeros)[:32]
        yield (instrs, iregs, oregs)


class EXTSTestCase(FHDLTestCase):
    CWD = os.path.dirname(os.path.realpath(__file__))
    ISAFN = os.path.normpath(os.path.join(CWD,
                                          "..", "..", "..", "..", "openpower", "isafunctions"))
    REGEX = re.compile(r"extsxl_(0x[0-9A-Fa-f]{16}).csv")
    XLENS = (64, 32, 16, 8)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pdecode = create_pdecode(include_fp=True)
        self.pdecode2 = PowerDecode2(pdecode)

    def run_tst(self, mapping, xlen):
        for (instrs, iregs, oregs) in tstgen(mapping):
            nr = len(instrs)
            with self.subTest():
                with Program(instrs, bigendian=False) as program:
                    sim = self.run_tst_program(program, iregs)
                    for (idx, gpr) in enumerate(range(nr)):
                        print(
                            f"{instrs[idx]} {iregs[idx]:016x} {oregs[idx]:016x}")
                        self.assertEqual(sim.gpr(gpr),
                                         SelectableInt(oregs[gpr], xlen))

    def test(self):
        data = {xlen: [] for xlen in EXTSTestCase.XLENS}
        wildcard = os.path.join(EXTSTestCase.ISAFN, "extsxl_*.csv")
        for path in glob.glob(wildcard):
            name = path[len(EXTSTestCase.ISAFN + os.path.sep):]
            match = EXTSTestCase.REGEX.match(name)
            if match is None:
                continue
            ireg = int(match[1], 16)
            with codecs.open(path, "rb", "UTF-8") as stream:
                csv_reader = csv.reader(stream, delimiter=",")
                _ = stream.readline()  # we already know the format
                for row in csv_reader:
                    assert len(row) == len(("instr",) + EXTSTestCase.XLENS)
                    row = tuple(map(lambda s: s.strip(), row))
                    instr = row[0]
                    xlens = dict(zip(
                        EXTSTestCase.XLENS,
                        map(lambda v: int(v, 16), row[1:])))
                    for (xlen, oreg) in xlens.items():
                        data[xlen].append((instr, ireg, oreg))

        # FIXME drop filter once XLEN != 64 is unlocked
        for xlen in filter(lambda v: v == 64, data):
            self.run_tst(data[xlen], xlen)

    def run_tst_program(self, prog, initial_regs=[0] * 32):
        simulator = run_tst(prog, initial_regs, pdecode2=self.pdecode2)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()

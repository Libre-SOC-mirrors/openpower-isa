# python code-writer for OpenPOWER ISA pseudo-code parsing

import os
import sys
import shutil
import subprocess
from openpower.decoder.pseudo.functionreader import ISAFunctions
from openpower.decoder.power_pseudo import convert_to_pure_python


def get_isafn_src_dir():
    fdir = os.path.abspath(os.path.dirname(__file__))
    fdir = os.path.split(fdir)[0]
    return os.path.join(fdir, "isafunctions")


header = """\
# auto-generated by pyfnwriter.py, do not edit or commit

from openpower.decoder.isa.caller import inject
from openpower.decoder.helpers import (EXTS, EXTS64, EXTZ64, ROTL64, ROTL32,
                                 MASK, MASK32,
                                 ne, eq, gt, ge, lt, le, ltu, gtu, length,
                                 trunc_divs, trunc_rems, MULS, DIVS, MODS,
                                 EXTS128, undefined,
                                 SINGLE,
                                 FPADD32, FPSUB32, FPMUL32, FPDIV32,
                                 FPADD64, FPSUB64, FPMUL64, FPDIV64,
                                )
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.selectable_int import selectconcat as concat

# %s
"""


class PyISAFnWriter(ISAFunctions):
    def __init__(self):
        ISAFunctions.__init__(self)
        self.pages_written = []

    def write_pysource(self, pagename):
        self.pages_written.append(pagename)
        function = self.fns[pagename]
        isadir = get_isafn_src_dir()
        os.makedirs(isadir, exist_ok=True)
        fname = os.path.join(isadir, "%s.py" % pagename)
        with open(fname, "w") as f:
            f.write(header % function['desc'])  # write out header
            # go through all instructions
            pcode = function['pcode']
            print(pcode)
            pycode = convert_to_pure_python(pcode)
            f.write(pycode)

    def write_isa_class(self):
        isadir = get_isafn_src_dir()
        fname = os.path.join(isadir, "all.py")

        with open(fname, "w") as f:
            helpers = []
            f.write('# auto-generated by pyfnwriter.py: do not edit or commit\n')
            f.write('from openpower.decoder.helpers import ISACallerHelper\n')
            for page in self.pages_written:
                module = 'openpower.decoder.isafunctions.' + page
                helper = 'ISACallerFnHelper_' + page
                helpers.append(helper)
                f.write('from %s import ISACallerFnHelper as %s\n' % (module, helper))
            f.write('\n')
            f.write('\n')
            f.write('class ISACallerFnHelper(%s):\n' % ', '.join(helpers + ['ISACallerHelper']))
            f.write('    pass\n')


def pyfnwriter():
    isa = PyISAFnWriter()
    write_isa_class = True
    if len(sys.argv) == 1:  # quick way to do it
        print(dir(isa))
        sources = isa.fns.keys()
    else:
        sources = sys.argv[1:]
        if sources[0] == "noall": # don't rewrite all.py
            write_isa_class = False
            sources.pop(0)
    print ("sources", write_isa_class, sources)
    for source in sources:
        isa.write_pysource(source)
    if write_isa_class:
        isa.write_isa_class()

if __name__ == '__main__':
    pyfnwriter()

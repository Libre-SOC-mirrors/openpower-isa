# python code-writer for OpenPOWER ISA pseudo-code parsing

import os
import sys
import shutil
import subprocess
from openpower.decoder.pseudo.pagereader import ISA
from openpower.decoder.power_pseudo import convert_to_python
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.caller import create_args


def get_isasrc_dir():
    fdir = os.path.abspath(os.path.dirname(__file__))
    fdir = os.path.split(fdir)[0]
    return os.path.join(fdir, "isa")


header = """\
# auto-generated by pywriter.py, do not edit or commit

from openpower.decoder.isa.caller import inject, instruction_info
from openpower.decoder.helpers import (EXTS, EXTS64, EXTZ64, ROTL64, ROTL32,
                                 MASK, MASK32,
                                 ne, eq, gt, ge, lt, le, ltu, gtu, length,
                                 trunc_divs, trunc_rems, MULS, DIVS, MODS,
                                 EXTS128, undefined,
                                 bitrev, SHL64,
                                 RANGE,
                                )
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.selectable_int import selectconcat as concat
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isafunctions.bcd import BCD_TO_DPD, DPD_TO_BCD

"""

fpheader = """
from openpower.decoder.helpers import (
                                 SINGLE,
                                 FPADD32, FPSUB32, FPMUL32, FPDIV32,
                                 FPADD64, FPSUB64, FPMUL64, FPDIV64,
                                 FPMULADD32,
                                 FPSIN32, FPCOS32,
                                )
from openpower.decoder.isafunctions.fpfromint import INT2FP
from openpower.decoder.isafunctions.double2single import DOUBLE

"""

iinfo_template = """instruction_info(func=%s,
                read_regs=%s,
                uninit_regs=%s, write_regs=%s,
                special_regs=%s, op_fields=%s,
                form='%s',
                asmregs=%s)"""


class PyISAWriter(ISA):
    def __init__(self):
        ISA.__init__(self)
        self.pages_written = []

    def write_pysource(self, pagename):
        self.pages_written.append(pagename)
        instrs = self.page[pagename]
        isadir = get_isasrc_dir()
        fname = os.path.join(isadir, "%s.py" % pagename)
        with open(fname, "w") as f:
            iinf = ''
            # write headers: FP gets extra imports
            f.write(header)  # write out header
            if (pagename.startswith("fp") or
                pagename.startswith("svfp")):
                f.write(fpheader)
            f.write("class %s:\n" % pagename)

            # go through all instructions
            for page in instrs:
                d = self.instr[page]
                print("page", pagename, page, fname, d.opcode)
                pcode = '\n'.join(d.pcode) + '\n'
                print(pcode)
                incl_carry = pagename == 'fixedshift'
                pycode, rused = convert_to_python(pcode, d.form, incl_carry)
                # create list of arguments to call
                regs = list(rused['read_regs']) + list(rused['uninit_regs'])
                regs += list(rused['special_regs'])
                args = ', '.join(create_args(regs, 'self'))
                # create list of arguments to return
                retargs = ', '.join(create_args(rused['write_regs']))
                # write out function.  pre-pend "op_" because some instrs are
                # also python keywords (cmp).  also replace "." with "_"
                op_fname = "op_%s" % page.replace(".", "_")
                f.write("    @inject()\n")
                f.write("    def %s(%s):\n" % (op_fname, args))
                # blech! this works in combination with ISACaller
                # @inject decorator, which works by injecting
                # global variables into the function namespace.
                for blech in ['NIA', 'end_loop']:
                    if blech in pycode:  # HACK - TODO fix
                        f.write("        global %s\n" % blech)
                pycode = pycode.split("\n")
                pycode = '\n'.join(map(lambda x: "        %s" % x, pycode))
                pycode = pycode.rstrip()
                f.write(pycode + '\n')
                if retargs:
                    f.write("        return (%s,)\n\n" % retargs)
                else:
                    f.write("\n")
                # accumulate the instruction info
                ops = repr(rused['op_fields'])
                iinfo = iinfo_template % (op_fname, rused['read_regs'],
                                          rused['uninit_regs'],
                                          rused['write_regs'],
                                          rused['special_regs'],
                                          ops, d.form, d.regs)
                iinf += "    %s_instrs['%s'] = %s\n" % (pagename, page, iinfo)
            # write out initialisation of info, for ISACaller to use
            f.write("    %s_instrs = {}\n" % pagename)
            f.write(iinf)

    def patch_if_needed(self, source):
        isadir = get_isasrc_dir()
        fname = os.path.join(isadir, "%s.py" % source)
        patchname = os.path.join(isadir, "%s.patch" % source)

        try:
            with open(patchname, 'r') as patch:
                newfname = fname + '.orig'
                shutil.copyfile(fname, newfname)
                subprocess.check_call(['patch', fname],
                                      stdin=patch)
        except:
            pass

    def write_isa_class(self):
        isadir = get_isasrc_dir()
        fname = os.path.join(isadir, "all.py")

        with open(fname, "w") as f:
            f.write('# auto-generated by pywriter.py: do not edit or commit\n')
            f.write('from openpower.decoder.isa.caller import ISACaller\n')
            for page in self.pages_written:
                f.write('from openpower.decoder.isa.%s ' \
                        'import %s\n' % (page, page))
            f.write('\n')

            classes = ', '.join(['ISACaller'] + self.pages_written)
            f.write('class ISA(%s):\n' % classes)
            f.write('    def __init__(self, *args, **kwargs):\n')
            f.write('        super().__init__(*args, **kwargs)\n')
            f.write('        self.instrs = {\n')
            for page in self.pages_written:
                f.write('            **self.%s_instrs,\n' % page)
            f.write('        }\n')


def pywriter():
    isa = PyISAWriter()
    write_isa_class = True
    if len(sys.argv) == 1:  # quick way to do it
        print(dir(isa))
        sources = isa.page.keys()
    else:
        sources = sys.argv[1:]
        if sources[0] == "noall": # don't rewrite all.py
            write_isa_class = False
            sources.pop(0)
    print ("sources", write_isa_class, sources)
    for source in sources:
        isa.write_pysource(source)
        isa.patch_if_needed(source)
    if write_isa_class:
        isa.write_isa_class()

if __name__ == '__main__':
    pywriter()

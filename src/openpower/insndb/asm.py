# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Funded by NLnet http://nlnet.nl

"""SVP64 OpenPOWER v3.0B assembly translator

This class takes raw svp64 assembly mnemonics (aliases excluded) and creates
an EXT001-encoded "svp64 prefix" (as a .long) followed by a v3.0B opcode.

It is very simple and straightforward, the only weirdness being the
extraction of the register information and conversion to v3.0B numbering.

Encoding format of svp64: https://libre-soc.org/openpower/sv/svp64/
Encoding format of arithmetic: https://libre-soc.org/openpower/sv/normal/
Encoding format of LDST: https://libre-soc.org/openpower/sv/ldst/
**TODO format of branches: https://libre-soc.org/openpower/sv/branches/**
**TODO format of CRs: https://libre-soc.org/openpower/sv/cr_ops/**
Bugtracker: https://bugs.libre-soc.org/show_bug.cgi?id=578
"""

import functools
import os
import sys
from collections import OrderedDict
import inspect

from openpower.decoder.pseudo.pagereader import ISA
from openpower.decoder.power_svp64 import SVP64RM, get_regtype, decode_extra
from openpower.decoder.selectable_int import SelectableInt
from openpower.consts import SVP64MODE
from openpower.insndb.core import SVP64Instruction
from openpower.insndb.core import Database
from openpower.insndb.core import Style
from openpower.insndb.core import WordInstruction
from openpower.decoder.power_enums import find_wiki_dir

# for debug logging
from openpower.util import log


DB = Database(find_wiki_dir())


class AssemblerError(ValueError):
    pass


# decodes svp64 assembly listings and creates EXT001 svp64 prefixes
class SVP64Asm:
    def __init__(self, lst, bigendian=False, macros=None):
        if macros is None:
            macros = {}
        self.macros = macros
        self.lst = lst
        self.trans = self.translate(lst)
        self.isa = ISA()  # reads the v3.0B pseudo-code markdown files
        self.svp64 = SVP64RM()  # reads the svp64 Remap entries for registers
        assert bigendian == False, "error, bigendian not supported yet"

    def __iter__(self):
        yield from self.trans

    def translate_one(self, insn, macros=None):
        if macros is None:
            macros = {}
        macros.update(self.macros)
        isa = self.isa
        svp64 = self.svp64
        insn_no_comments = insn.partition('#')[0].strip()
        if not insn_no_comments:
            return

        # find first space, to get opcode
        ls = insn_no_comments.split()
        opcode = ls[0]
        # now find opcode fields
        fields = ''.join(ls[1:]).split(',')
        mfields = list(filter(bool, map(str.strip, fields)))
        log("opcode, fields", ls, opcode, mfields)
        fields = []
        # macro substitution
        for field in mfields:
            fields.append(macro_subst(macros, field))
        log("opcode, fields substed", ls, opcode, fields)

        # identify if it is a word instruction
        record = DB[opcode]
        #log("record", record)
        if record is not None:
            insn = WordInstruction.assemble(record=record, arguments=fields)
            yield from insn.disassemble(record=record, style=Style.LEGACY)
            return

        # identify if is a svp64 mnemonic
        if not opcode.startswith('sv.'):
            yield insn  # unaltered
            return
        opcode = opcode[3:]  # strip leading "sv"

        # start working on decoding the svp64 op: sv.basev30Bop/vec2/mode
        opmodes = opcode.split("/")  # split at "/"
        v30b_op = opmodes.pop(0)    # first is the v3.0B

        record = DB[v30b_op]
        #log("record v30b", record)
        if record is not None:
            insn = SVP64Instruction.assemble(record=record,
                arguments=fields, specifiers=opmodes)
            yield from insn.disassemble(record=record, style=Style.LEGACY)
            return

        raise AssemblerError(insn_no_comments)

    def translate(self, lst):
        for insn in lst:
            yield from self.translate_one(insn)


def macro_subst(macros, txt):
    again = True
    log("subst", txt, macros)
    while again:
        again = False
        for macro, value in macros.items():
            if macro == txt:
                again = True
                replaced = txt.replace(macro, value)
                log("macro", txt, "replaced", replaced, macro, value)
                txt = replaced
                continue
            toreplace = '%s.s' % macro
            if toreplace == txt:
                again = True
                replaced = txt.replace(toreplace, "%s.s" % value)
                log("macro", txt, "replaced", replaced, toreplace, value)
                txt = replaced
                continue
            toreplace = '%s.v' % macro
            if toreplace == txt:
                again = True
                replaced = txt.replace(toreplace, "%s.v" % value)
                log("macro", txt, "replaced", replaced, toreplace, value)
                txt = replaced
                continue
            toreplace = '*%s' % macro
            if toreplace in txt:
                again = True
                replaced = txt.replace(toreplace, '*%s' % value)
                log("macro", txt, "replaced", replaced, toreplace, value)
                txt = replaced
                continue
            toreplace = '(%s)' % macro
            if toreplace in txt:
                again = True
                replaced = txt.replace(toreplace, '(%s)' % value)
                log("macro", txt, "replaced", replaced, toreplace, value)
                txt = replaced
                continue
    log("    processed", txt)
    return txt


def get_ws(line):
    # find whitespace
    ws = ''
    while line:
        if not line[0].isspace():
            break
        ws += line[0]
        line = line[1:]
    return ws, line


def main():
    # get an input file and an output file
    args = sys.argv[1:]
    if len(args) == 0:
        infile = sys.stdin
        outfile = sys.stdout
        # read the whole lot in advance in case of in-place
        lines = list(infile.readlines())
    elif len(args) != 2:
        print("pysvp64asm [infile | -] [outfile | -]", file=sys.stderr)
        exit(0)
    else:
        if args[0] == '--':
            infile = sys.stdin
        else:
            infile = open(args[0], "r")
        # read the whole lot in advance in case of in-place overwrite
        lines = list(infile.readlines())

        if args[1] == '--':
            outfile = sys.stdout
        else:
            outfile = open(args[1], "w")

    # read the line, look for custom insn, process it
    macros = {}  # macros which start ".set"
    isa = SVP64Asm([])
    for line in lines:
        op = line.split("#")[0].strip()
        # identify macros
        if op.startswith(".set"):
            macro = op[4:].split(",")
            (macro, value) = map(str.strip, macro)
            macros[macro] = value

        if not op or op.startswith("#"):
            outfile.write(line)
            continue
        (ws, line) = get_ws(line)
        lst = isa.translate_one(op, macros)
        lst = '; '.join(lst)
        outfile.write("%s%s # %s\n" % (ws, lst, op))


if __name__ == '__main__':
    lst = ['slw 3, 1, 4',
           'extsw 5, 3',
           'sv.extsw 5, 3',
           'sv.cmpi 5, 1, 3, 2',
           'sv.setb 5, 31',
           'sv.isel 64.v, 3, 2, 65.v',
           'sv.setb/dm=r3/sm=1<<r3 5, 31',
           'sv.setb/m=r3 5, 31',
           'sv.setb/vec2 5, 31',
           'sv.setb/sw=8/ew=16 5, 31',
           'sv.extsw./ff=eq 5, 31',
           'sv.extsw./satu/sz/dz/sm=r3/dm=r3 5, 31',
           'sv.add. 5.v, 2.v, 1.v',
           'sv.add./m=r3 5.v, 2.v, 1.v',
           ]
    lst += [
        'sv.stw 5.v, 4(1.v)',
        'sv.ld 5.v, 4(1.v)',
        'setvl. 2, 3, 4, 0, 1, 1',
        'sv.setvl. 2, 3, 4, 0, 1, 1',
    ]
    lst = [
        "sv.stfsu 0.v, 16(4.v)",
    ]
    lst = [
        "sv.stfsu/els 0.v, 16(4)",
    ]
    lst = [
        'sv.add./mr 5.v, 2.v, 1.v',
    ]
    macros = {'win2': '50', 'win': '60'}
    lst = [
        'sv.addi win2.v, win.v, -1',
        'sv.add./mrr 5.v, 2.v, 1.v',
        #'sv.lhzsh 5.v, 11(9.v), 15',
        #'sv.lwzsh 5.v, 11(9.v), 15',
        'sv.ffmadds 6.v, 2.v, 4.v, 6.v',
    ]
    lst = [
        #'sv.fmadds 0.v, 8.v, 16.v, 4.v',
        #'sv.ffadds 0.v, 8.v, 4.v',
        'svremap 11, 0, 1, 2, 3, 2, 1',
        'svshape 8, 1, 1, 1, 0',
        'svshape 8, 1, 1, 1, 1',
    ]
    lst = [
        #'sv.lfssh 4.v, 11(8.v), 15',
        #'sv.lwzsh 4.v, 11(8.v), 15',
        #'sv.svstep. 2.v, 4, 0',
        #'sv.fcfids. 48.v, 64.v',
        'sv.fcoss. 80.v, 0.v',
        'sv.fcoss. 20.v, 0.v',
    ]
    lst = [
        'sv.bc/all 3,12,192',
        'sv.bclr/vsbi 3,81.v,192',
        'sv.ld 5.v, 4(1.v)',
        'sv.svstep. 2.v, 4, 0',
    ]
    lst = [
        'minmax 3,12,5,3',
        'minmax. 3,12,5,4',
        'avgadd 3,12,5',
        'absdu 3,12,5',
        'absds 3,12,5',
        'absdacu 3,12,5',
        'absdacs 3,12,5',
        'cprop 3,12,5',
        'svindex 0,0,1,0,0,0,0',
    ]
    lst = [
        'sv.svstep./m=r3 2.v, 4, 0',
        'ternlogi 0,0,0,0x5',
        'fmvis 5,65535',
        'fmvis 5,1',
        'fmvis 5,2',
        'fmvis 5,4',
        'fmvis 5,8',
        'fmvis 5,16',
        'fmvis 5,32',
        'fmvis 5,64',
        'fmvis 5,32768',
    ]
    lst = [
        'sv.andi. *80, *80, 1',
        'sv.ffmadds. 6.v, 2.v, 4.v, 6.v',  # incorrectly inserted 32-bit op
        'sv.ffmadds 6.v, 2.v, 4.v, 6.v',  # correctly converted to .long
        'svshape2 8, 1, 31, 7, 1, 1',
        'sv.ld 5.v, 4(1.v)',
        'sv.stw 5.v, 4(1.v)',
        'sv.bc/all 3,12,192',
        'pcdec. 0,0,0,0',
    ]
    lst = [
        #"sv.cmp/ff=gt *0,*1,*2,0",
        #"dsld 5,4,5,3",
        "crfbinlog 3,4,5,15",
        #"crbinlog 3,4,5",
    ]
    isa = SVP64Asm(lst, macros=macros)
    log("list:\n", "\n\t".join(list(isa)))
    # running svp64.py is designed to test hard-coded lists
    # (above) - which strictly speaking should all be unit tests.
    # if you need to actually do assembler translation at the
    # commandline use "pysvp64asm" - see setup.py
    # XXX NO. asm_process()

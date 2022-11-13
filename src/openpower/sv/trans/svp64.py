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
from openpower.decoder.power_insn import SVP64Instruction
from openpower.decoder.power_insn import Database
from openpower.decoder.power_insn import WordInstruction
from openpower.decoder.power_enums import find_wiki_dir

# for debug logging
from openpower.util import log


# decode GPR into sv extra
def get_extra_gpr(etype, regmode, field):
    if regmode == 'scalar':
        # cut into 2-bits 5-bits SS FFFFF
        sv_extra = field >> 5
        field = field & 0b11111
    else:
        # cut into 5-bits 2-bits FFFFF SS
        sv_extra = field & 0b11
        field = field >> 2
    return sv_extra, field


# decode 3-bit CR into sv extra
def get_extra_cr_3bit(etype, regmode, field):
    if regmode == 'scalar':
        # cut into 2-bits 3-bits SS FFF
        sv_extra = field >> 3
        field = field & 0b111
    else:
        # cut into 3-bits 4-bits FFF SSSS but will cut 2 zeros off later
        sv_extra = field & 0b1111
        field = field >> 4
    return sv_extra, field


# decodes SUBVL
def decode_subvl(encoding):
    pmap = {'2': 0b01, '3': 0b10, '4': 0b11}
    assert encoding in pmap, \
        "encoding %s for SUBVL not recognised" % encoding
    return pmap[encoding]


# decodes elwidth
def decode_elwidth(encoding):
    pmap = {'8': 0b11, '16': 0b10, '32': 0b01}
    assert encoding in pmap, \
        "encoding %s for elwidth not recognised" % encoding
    return pmap[encoding]


# decodes predicate register encoding
def decode_predicate(encoding):
    pmap = {  # integer
        '1<<r3': (0, 0b001),
        'r3': (0, 0b010),
        '~r3': (0, 0b011),
        'r10': (0, 0b100),
        '~r10': (0, 0b101),
        'r30': (0, 0b110),
        '~r30': (0, 0b111),
        # CR
        'lt': (1, 0b000),
        'nl': (1, 0b001), 'ge': (1, 0b001),  # same value
        'gt': (1, 0b010),
        'ng': (1, 0b011), 'le': (1, 0b011),  # same value
        'eq': (1, 0b100),
        'ne': (1, 0b101),
        'so': (1, 0b110), 'un': (1, 0b110),  # same value
        'ns': (1, 0b111), 'nu': (1, 0b111),  # same value
    }
    assert encoding in pmap, \
        "encoding %s for predicate not recognised" % encoding
    return pmap[encoding]


# decodes "Mode" in similar way to BO field (supposed to, anyway)
def decode_bo(encoding):
    pmap = {  # TODO: double-check that these are the same as Branch BO
        'lt': 0b000,
        'nl': 0b001, 'ge': 0b001,  # same value
        'gt': 0b010,
        'ng': 0b011, 'le': 0b011,  # same value
        'eq': 0b100,
        'ne': 0b101,
        'so': 0b110, 'un': 0b110,  # same value
        'ns': 0b111, 'nu': 0b111,  # same value
    }
    assert encoding in pmap, \
        "encoding %s for BO Mode not recognised" % encoding
    # barse-ackwards MSB0/LSB0. sigh.  this would be nice to be the
    # same as the decode_predicate() CRfield table above, but (inv,CRbit)
    # is how it is in the spec [decode_predicate is (CRbit,inv)]
    mapped = pmap[encoding]
    si = SelectableInt(0, 3)
    si[0] = mapped & 1  # inv
    si[1:3] = mapped >> 1  # CR
    return int(si)


# partial-decode fail-first mode
def decode_ffirst(encoding):
    if encoding in ['RC1', '~RC1']:
        return encoding
    return decode_bo(encoding)


def decode_reg(field, macros=None):
    if macros is None:
        macros = {}
    # decode the field number. "5.v" or "3.s" or "9"
    # and now also "*0", and "*%0".  note: *NOT* to add "*%rNNN" etc.
    # https://bugs.libre-soc.org/show_bug.cgi?id=884#c0
    if field.startswith(("*%", "*")):
        if field.startswith("*%"):
            field = field[2:]
        else:
            field = field[1:]
        while field in macros:
            field = macros[field]
        return int(field), "vector"  # actual register number

    # try old convention (to be retired)
    field = field.split(".")
    regmode = 'scalar'  # default
    if len(field) == 2:
        if field[1] == 's':
            regmode = 'scalar'
        elif field[1] == 'v':
            regmode = 'vector'
    field = int(field[0])  # actual register number
    return field, regmode


def decode_imm(field):
    ldst_imm = "(" in field and field[-1] == ')'
    if ldst_imm:
        return field[:-1].split("(")
    else:
        return None, field


def crf_extra(etype, rname, extra_idx, regmode, field, extras):
    """takes a CR Field number (CR0-CR127), splits into EXTRA2/3 and v3.0
    the scalar/vector mode (crNN.v or crNN.s) changes both the format
    of the EXTRA2/3 encoding as well as what range of registers is possible.
    this function can be used for both BF/BFA and BA/BB/BT by first removing
    the bottom 2 bits of BA/BB/BT then re-instating them after encoding.
    see https://libre-soc.org/openpower/sv/svp64/appendix/#cr_extra
    for specification
    """
    sv_extra, field = get_extra_cr_3bit(etype, regmode, field)
    # now sanity-check (and shrink afterwards)
    if etype == 'EXTRA2':
        # 3-bit CR Field (BF, BFA) EXTRA2 encoding
        if regmode == 'scalar':
            # range is CR0-CR15 in increments of 1
            assert (sv_extra >> 1) == 0, \
                "scalar CR %s cannot fit into EXTRA2 %s" % \
                (rname, str(extras[extra_idx]))
            # all good: encode as scalar
            sv_extra = sv_extra & 0b01
        else:  # vector
            # range is CR0-CR127 in increments of 16
            assert sv_extra & 0b111 == 0, \
                "vector CR %s cannot fit into EXTRA2 %s" % \
                (rname, str(extras[extra_idx]))
            # all good: encode as vector (bit 2 set)
            sv_extra = 0b10 | (sv_extra >> 3)
    else:
        # 3-bit CR Field (BF, BFA) EXTRA3 encoding
        if regmode == 'scalar':
            # range is CR0-CR31 in increments of 1
            assert (sv_extra >> 2) == 0, \
                "scalar CR %s cannot fit into EXTRA3 %s" % \
                (rname, str(extras[extra_idx]))
            # all good: encode as scalar
            sv_extra = sv_extra & 0b11
        else:  # vector
            # range is CR0-CR127 in increments of 8
            assert sv_extra & 0b11 == 0, \
                "vector CR %s cannot fit into EXTRA3 %s" % \
                (rname, str(extras[extra_idx]))
            # all good: encode as vector (bit 3 set)
            sv_extra = 0b100 | (sv_extra >> 2)
    return sv_extra, field


def to_number(field):
    if field.startswith("0x"):
        return eval(field)
    if field.startswith("0b"):
        return eval(field)
    return int(field)


DB = Database(find_wiki_dir())


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
        insn_no_comments = insn.partition('#')[0]
        # find first space, to get opcode
        ls = insn_no_comments.split()
        opcode = ls[0]
        # now find opcode fields
        fields = ''.join(ls[1:]).split(',')
        mfields = list(map(str.strip, fields))
        log("opcode, fields", ls, opcode, mfields)
        fields = []
        # macro substitution
        for field in mfields:
            fields.append(macro_subst(macros, field))
        log("opcode, fields substed", ls, opcode, fields)

        # identify if it is a word instruction
        record = None
        if os.environ.get("INSNDB"):
            record = DB[opcode]
        if record is not None:
            insn = WordInstruction.assemble(db=DB,
                opcode=opcode, arguments=fields)
            yield " ".join((
                f".long 0x{int(insn):08X}",
                "#",
                opcode,
                ",".join(fields),
            ))
            return

        # identify if is a svp64 mnemonic
        if not opcode.startswith('sv.'):
            yield insn  # unaltered
            return
        opcode = opcode[3:]  # strip leading "sv"

        # start working on decoding the svp64 op: sv.basev30Bop/vec2/mode
        opmodes = opcode.split("/")  # split at "/"
        v30b_op_orig = opmodes.pop(0)    # first is the v3.0B
        # check instruction ends with dot
        rc_mode = v30b_op_orig.endswith('.')
        if rc_mode:
            v30b_op = v30b_op_orig[:-1]
        else:
            v30b_op = v30b_op_orig

        record = None
        if os.environ.get("INSNDB"):
            record = DB[v30b_op]
        if record is not None:
            insn = SVP64Instruction.assemble(db=DB,
                opcode=v30b_op_orig,
                arguments=fields,
                specifiers=opmodes)
            prefix = int(insn.prefix)
            suffix = int(insn.suffix)
            yield " ".join((
                f".long 0x{prefix:08X};",
                f".long 0x{suffix:08X};",
                "#",
                opcode,
                ",".join(fields),
            ))
            return

        # look up the 32-bit op (original, with "." if it has it)
        if v30b_op_orig in isa.instr:
            isa_instr = isa.instr[v30b_op_orig]
        else:
            raise Exception("opcode %s of '%s' not supported" %
                            (v30b_op_orig, insn))

        # look up the svp64 op, first the original (with "." if it has it)
        if v30b_op_orig in svp64.instrs:
            rm = svp64.instrs[v30b_op_orig]  # one row of the svp64 RM CSV
        # then without the "." (if there was one)
        elif v30b_op in svp64.instrs:
            rm = svp64.instrs[v30b_op]  # one row of the svp64 RM CSV
        else:
            raise Exception(f"opcode {v30b_op_orig!r} of "
                            f"{insn!r} not an svp64 instruction")

        # get regs info e.g. "RT,RA,RB"
        v30b_regs = isa_instr.regs[0]
        log("v3.0B op", v30b_op, "Rc=1" if rc_mode else '')
        log("v3.0B regs", opcode, v30b_regs)
        log("RM", rm)

        # right.  the first thing to do is identify the ordering of
        # the registers, by name.  the EXTRA2/3 ordering is in
        # rm['0']..rm['3'] but those fields contain the names RA, BB
        # etc.  we have to read the pseudocode to understand which
        # reg is which in our instruction. sigh.

        # first turn the svp64 rm into a "by name" dict, recording
        # which position in the RM EXTRA it goes into
        # also: record if the src or dest was a CR, for sanity-checking
        # (elwidth overrides on CRs are banned)
        decode = decode_extra(rm)
        dest_reg_cr, src_reg_cr, svp64_src, svp64_dest = decode

        log("EXTRA field index, src", svp64_src)
        log("EXTRA field index, dest", svp64_dest)

        # okaaay now we identify the field value (opcode N,N,N) with
        # the pseudo-code info (opcode RT, RA, RB)
        assert len(fields) == len(v30b_regs), \
            "length of fields %s must match insn `%s` fields %s" % \
            (str(v30b_regs), insn, str(fields))
        opregfields = zip(fields, v30b_regs)  # err that was easy

        # now for each of those find its place in the EXTRA encoding
        # note there is the possibility (for LD/ST-with-update) of
        # RA occurring **TWICE**.  to avoid it getting added to the
        # v3.0B suffix twice, we spot it as a duplicate, here
        extras = OrderedDict()
        for idx, (field, regname) in enumerate(opregfields):
            imm, regname = decode_imm(regname)
            rtype = get_regtype(regname)
            log("    idx find", rtype, idx, field, regname, imm)
            if rtype is None:
                # probably an immediate field, append it straight
                extras[('imm', idx, False)] = (idx, field, None, None, None)
                continue
            extra = svp64_src.get(regname, None)
            if extra is not None:
                extra = ('s', extra, False)  # not a duplicate
                extras[extra] = (idx, field, regname, rtype, imm)
                log("    idx src", idx, extra, extras[extra])
            dextra = svp64_dest.get(regname, None)
            log("regname in", regname, dextra)
            if dextra is not None:
                is_a_duplicate = extra is not None  # duplicate spotted
                dextra = ('d', dextra, is_a_duplicate)
                extras[dextra] = (idx, field, regname, rtype, imm)
                log("    idx dst", idx, extra, extras[dextra])

        # great! got the extra fields in their associated positions:
        # also we know the register type. now to create the EXTRA encodings
        etype = rm['Etype']  # Extra type: EXTRA3/EXTRA2
        ptype = rm['Ptype']  # Predication type: Twin / Single
        extra_bits = 0
        v30b_newfields = []
        for extra_idx, (idx, field, rname, rtype, iname) in extras.items():
            # is it a field we don't alter/examine?  if so just put it
            # into newfields
            if rtype is None:
                v30b_newfields.append(field)
                continue

            # identify if this is a ld/st immediate(reg) thing
            ldst_imm = "(" in field and field[-1] == ')'
            if ldst_imm:
                immed, field = field[:-1].split("(")

            field, regmode = decode_reg(field, macros=macros)
            log("    ", extra_idx, rname, rtype,
                regmode, iname, field, end=" ")

            # see Mode field https://libre-soc.org/openpower/sv/svp64/
            # XXX TODO: the following is a bit of a laborious repeated
            # mess, which could (and should) easily be parameterised.
            # XXX also TODO: the LD/ST modes which are different
            # https://libre-soc.org/openpower/sv/ldst/

            # rright.  SVP64 register numbering is from 0 to 127
            # for GPRs, FPRs *and* CR Fields, where for v3.0 the GPRs and RPFs
            # are 0-31 and CR Fields are only 0-7.  the SVP64 RM "Extra"
            # area is used to extend the numbering from the 32-bit
            # instruction, and also to record whether the register
            # is scalar or vector. on a per-operand basis.  this
            # results in a slightly finnicky encoding: here we go...

            # encode SV-GPR and SV-FPR field into extra, v3.0field
            if rtype in ['GPR', 'FPR']:
                sv_extra, field = get_extra_gpr(etype, regmode, field)
                # now sanity-check. EXTRA3 is ok, EXTRA2 has limits
                # (and shrink to a single bit if ok)
                if etype == 'EXTRA2':
                    if regmode == 'scalar':
                        # range is r0-r63 in increments of 1
                        assert (sv_extra >> 1) == 0, \
                            "scalar GPR %s cannot fit into EXTRA2 %s" % \
                            (rname, str(extras[extra_idx]))
                        # all good: encode as scalar
                        sv_extra = sv_extra & 0b01
                    else:
                        # range is r0-r127 in increments of 2 (r0 r2 ... r126)
                        assert sv_extra & 0b01 == 0, \
                            "%s: vector field %s cannot fit " \
                            "into EXTRA2 %s" % \
                            (insn, rname, str(extras[extra_idx]))
                        # all good: encode as vector (bit 2 set)
                        sv_extra = 0b10 | (sv_extra >> 1)
                elif regmode == 'vector':
                    # EXTRA3 vector bit needs marking
                    sv_extra |= 0b100

            # encode SV-CR 3-bit field into extra, v3.0field.
            # 3-bit is for things like BF and BFA
            elif rtype == 'CR_3bit':
                sv_extra, field = crf_extra(etype, rname, extra_idx,
                                            regmode, field, extras)

            # encode SV-CR 5-bit field into extra, v3.0field
            # 5-bit is for things like BA BB BC BT etc.
            # *sigh* this is the same as 3-bit except the 2 LSBs of the
            # 5-bit field are passed through unaltered.
            elif rtype == 'CR_5bit':
                cr_subfield = field & 0b11  # record bottom 2 bits for later
                field = field >> 2         # strip bottom 2 bits
                # use the exact same 3-bit function for the top 3 bits
                sv_extra, field = crf_extra(etype, rname, extra_idx,
                                            regmode, field, extras)
                # reconstruct the actual 5-bit CR field (preserving the
                # bottom 2 bits, unaltered)
                field = (field << 2) | cr_subfield

            else:
                raise Exception("no type match: %s" % rtype)

            # capture the extra field info
            log("=>", "%5s" % bin(sv_extra), field)
            extras[extra_idx] = sv_extra

            # append altered field value to v3.0b, differs for LDST
            # note that duplicates are skipped e.g. EXTRA2 contains
            # *BOTH* s:RA *AND* d:RA which happens on LD/ST-with-update
            srcdest, idx, duplicate = extra_idx
            if duplicate:  # skip adding to v3.0b fields, already added
                continue
            if ldst_imm:
                v30b_newfields.append(("%s(%s)" % (immed, str(field))))
            else:
                v30b_newfields.append(str(field))

        log("new v3.0B fields", v30b_op, v30b_newfields)
        log("extras", extras)

        # rright. now we have all the info. start creating SVP64 instruction.
        svp64_insn = SVP64Instruction.pair(prefix=0, suffix=0)
        svp64_prefix = svp64_insn.prefix
        svp64_rm = svp64_insn.prefix.rm

        # begin with EXTRA fields
        for idx, sv_extra in extras.items():
            log(idx)
            if idx is None:
                continue
            if idx[0] == 'imm':
                continue
            srcdest, idx, duplicate = idx
            if etype == 'EXTRA2':
                svp64_rm.extra2[idx] = sv_extra
            else:
                svp64_rm.extra3[idx] = sv_extra

        # identify if the op is a LD/ST.
        # see https://libre-soc.org/openpower/sv/ldst/
        is_ldst = rm['mode'] in ['LDST_IDX', 'LDST_IMM']
        is_ldst_idx = rm['mode'] == 'LDST_IDX'
        is_ldst_imm = rm['mode'] == 'LDST_IMM'
        is_ld = v30b_op.startswith("l") and is_ldst
        is_st = v30b_op.startswith("s") and is_ldst

        # branch-conditional or CR detection
        is_bc = rm['mode'] == 'BRANCH'
        is_cr = rm['mode'] == 'CROP'

        # parts of svp64_rm
        mmode = 0  # bit 0
        pmask = 0  # bits 1-3
        destwid = 0  # bits 4-5
        srcwid = 0  # bits 6-7
        subvl = 0   # bits 8-9
        smask = 0  # bits 16-18 but only for twin-predication
        mode = 0  # bits 19-23

        mask_m_specified = False
        has_pmask = False
        has_smask = False

        saturation = None
        src_zero = 0
        dst_zero = 0
        sv_mode = None

        mapreduce = False
        reverse_gear = False
        mapreduce_crm = False

        predresult = False
        failfirst = False
        ldst_elstride = 0
        ldst_postinc = 0
        sea = False

        vli = False
        sea = False

        # ok let's start identifying opcode augmentation fields
        for encmode in opmodes:
            # predicate mask (src and dest)
            if encmode.startswith("m="):
                pme = encmode
                pmmode, pmask = decode_predicate(encmode[2:])
                smmode, smask = pmmode, pmask
                mmode = pmmode
                mask_m_specified = True
            # predicate mask (dest)
            elif encmode.startswith("dm="):
                pme = encmode
                pmmode, pmask = decode_predicate(encmode[3:])
                mmode = pmmode
                has_pmask = True
            # predicate mask (src, twin-pred)
            elif encmode.startswith("sm="):
                sme = encmode
                smmode, smask = decode_predicate(encmode[3:])
                mmode = smmode
                has_smask = True
            # vec2/3/4
            elif encmode.startswith("vec"):
                subvl = decode_subvl(encmode[3:])
            # elwidth (both src and dest, like mask)
            elif encmode.startswith("w="):
                destwid = decode_elwidth(encmode[2:])
                srcwid = decode_elwidth(encmode[2:])
            # just dest width
            elif encmode.startswith("dw="):
                destwid = decode_elwidth(encmode[3:])
            # just src width
            elif encmode.startswith("sw="):
                srcwid = decode_elwidth(encmode[3:])
            # post-increment
            elif encmode == 'pi':
                ldst_postinc = 1
                # in indexed mode, set sv_mode=0b00
                assert is_ldst_imm is True
                sv_mode = 0b00
            # element-strided LD/ST
            elif encmode == 'els':
                ldst_elstride = 1
                # in indexed mode, set sv_mode=0b01
                if is_ldst_idx:
                    sv_mode = 0b01
            # saturation
            elif encmode == 'sats':
                assert sv_mode is None
                saturation = 1
                sv_mode = 0b10
            elif encmode == 'satu':
                assert sv_mode is None
                sv_mode = 0b10
                saturation = 0
            # predicate zeroing
            elif encmode == 'zz':  # TODO, a lot more checking on legality
                dst_zero = 1      # NOT on cr_ops, that's RM[6]
                src_zero = 1
            elif encmode == 'sz':
                src_zero = 1
            elif encmode == 'dz':
                dst_zero = 1
            # failfirst
            elif encmode.startswith("ff="):
                assert sv_mode is None
                if is_cr: # sigh, CROPs is different
                    sv_mode = 0b10
                else:
                    sv_mode = 0b01
                failfirst = decode_ffirst(encmode[3:])
                assert sea is False, "cannot use failfirst with signed-address"
            # predicate-result, interestingly same as fail-first
            elif encmode.startswith("pr="):
                assert sv_mode is None
                sv_mode = 0b11
                predresult = decode_ffirst(encmode[3:])
            # map-reduce mode, reverse-gear
            elif encmode == 'mrr':
                assert sv_mode is None
                sv_mode = 0b00
                mapreduce = True
                reverse_gear = True
            # map-reduce mode
            elif encmode == 'mr':
                assert sv_mode is None
                sv_mode = 0b00
                mapreduce = True
            elif encmode == 'crm':  # CR on map-reduce
                assert sv_mode is None
                sv_mode = 0b00
                mapreduce_crm = True
            elif encmode == 'vli':
                assert failfirst is not False, "VLi only allowed in failfirst"
                vli = True
            elif encmode == 'sea':
                assert is_ldst_idx
                sea = True
                assert failfirst is False, "cannot use ffirst+signed-address"
            elif is_bc:
                if encmode == 'all':
                    svp64_rm.branch.ALL = 1
                elif encmode == 'snz':
                    svp64_rm.branch.sz = 1
                    svp64_rm.branch.SNZ = 1
                elif encmode == 'sl':
                    svp64_rm.branch.SL = 1
                elif encmode == 'slu':
                    svp64_rm.branch.SLu = 1
                elif encmode == 'lru':
                    svp64_rm.branch.LRu = 1
                elif encmode == 'vs':
                    svp64_rm.branch.VLS = 1
                elif encmode == 'vsi':
                    svp64_rm.branch.VLS = 1
                    svp64_rm.branch.vls.VLi = 1
                elif encmode == 'vsb':
                    svp64_rm.branch.VLS = 1
                    svp64_rm.branch.vls.VSb = 1
                elif encmode == 'vsbi':
                    svp64_rm.branch.VLS = 1
                    svp64_rm.branch.vls.VSb = 1
                    svp64_rm.branch.vls.VLi = 1
                elif encmode == 'ctr':
                    svp64_rm.branch.CTR = 1
                elif encmode == 'cti':
                    svp64_rm.branch.CTR = 1
                    svp64_rm.branch.ctr.CTi = 1
                else:
                    raise AssertionError("unknown encmode %s" % encmode)
            else:
                raise AssertionError("unknown encmode %s" % encmode)

        # post-inc only available on ld-with-update
        if ldst_postinc:
            assert "u" in opcode, "/pi only available on ld/st-update"

        # sanity check if dz/zz used in branch-mode
        if is_bc and dst_zero:
            raise AssertionError("dz/zz not supported in branch, use 'sz'")

        # check sea *after* all qualifiers are evaluated
        if sea:
            assert sv_mode in (None, 0b00, 0b01)

        if ptype == '2P':
            # since m=xx takes precedence (overrides) sm=xx and dm=xx,
            # treat them as mutually exclusive
            if mask_m_specified:
                assert not has_smask,\
                    "cannot have both source-mask and predicate mask"
                assert not has_pmask,\
                    "cannot have both dest-mask and predicate mask"
            # since the default is INT predication (ALWAYS), if you
            # specify one CR mask, you must specify both, to avoid
            # mixing INT and CR reg types
            if has_pmask and pmmode == 1:
                assert has_smask, \
                    "need explicit source-mask in CR twin predication"
            if has_smask and smmode == 1:
                assert has_pmask, \
                    "need explicit dest-mask in CR twin predication"
            # sanity-check that 2Pred mask is same mode
            if has_pmask and has_smask:
                assert smmode == pmmode, \
                    "predicate masks %s and %s must be same reg type" % \
                    (pme, sme)

        # sanity-check that twin-predication mask only specified in 2P mode
        if ptype == '1P':
            assert not has_smask, \
                "source-mask can only be specified on Twin-predicate ops"
            assert not has_pmask, \
                "dest-mask can only be specified on Twin-predicate ops"

        # construct the mode field, doing sanity-checking along the way
        if src_zero:
            assert has_smask or mask_m_specified, \
                "src zeroing requires a source predicate"
        if dst_zero:
            assert has_pmask or mask_m_specified, \
                "dest zeroing requires a dest predicate"

        # okaaay, so there are 4 different modes, here, which will be
        # partly-merged-in: is_ldst is merged in with "normal", but
        # is_bc is so different it's done separately.  likewise is_cr
        # (when it is done).  here are the maps:

        # for "normal" arithmetic: https://libre-soc.org/openpower/sv/normal/
        """
            | 0-1 |  2  |  3   4  |  description              |
            | --- | --- |---------|-------------------------- |
            | 00  |   0 |  dz  sz | simple mode                      |
            | 00  |   1 | 0  RG   | scalar reduce mode (mapreduce) |
            | 01  | inv | CR-bit  | Rc=1: ffirst CR sel              |
            | 01  | inv | VLi RC1 |  Rc=0: ffirst z/nonz |
            | 10  |   N | dz   sz |  sat mode: N=0/1 u/s |
            | 11  | inv | CR-bit  |  Rc=1: pred-result CR sel |
            | 11  | inv | zz  RC1 |  Rc=0: pred-result z/nonz |
        """

        # https://libre-soc.org/openpower/sv/ldst/
        # for LD/ST-immediate:
        """
            | 0-1 |  2  |  3   4  |  description               |
            | --- | --- |---------|--------------------------- |
            | 00  | 0   |  zz els | normal mode                |
            | 00  | 1   | pi  lf  | post-inc, LD-fault-first   |
            | 01  | inv | CR-bit  | Rc=1: ffirst CR sel        |
            | 01  | inv | els RC1 |  Rc=0: ffirst z/nonz       |
            | 10  |   N | zz  els |  sat mode: N=0/1 u/s       |
            | 11  | inv | CR-bit  |  Rc=1: pred-result CR sel  |
            | 11  | inv | els RC1 |  Rc=0: pred-result z/nonz  |
        """

        # for LD/ST-indexed (RA+RB):
        """
            | 0-1 |  2  |  3   4  |  description                 |
            | --- | --- |---------|----------------------------- |
            | 00  | SEA |  dz  sz | normal mode                  |
            | 01  | SEA |  dz sz  | strided (scalar only source) |
            | 10  |   N | dz   sz | sat mode: N=0/1 u/s          |
            | 11  | inv | CR-bit  | Rc=1: pred-result CR sel     |
            | 11  | inv | dz  RC1 | Rc=0: pred-result z/nonz     |
        """

        # and leaving out branches and cr_ops for now because they're
        # under development
        """ TODO branches and cr_ops
        """

        if is_bc:
            sv_mode = int(svp64_rm.mode[0, 1])
            if src_zero:
                svp64_rm.branch.sz = 1

        else:
            ######################################
            # "element-strided" mode, ldst_idx
            if sv_mode == 0b01 and is_ldst_idx:
                mode |= src_zero << SVP64MODE.SZ  # predicate zeroing
                mode |= dst_zero << SVP64MODE.DZ  # predicate zeroing
                mode |= sea << SVP64MODE.SEA  # el-strided

            ######################################
            # "normal" mode
            elif sv_mode is None:
                mode |= src_zero << SVP64MODE.SZ  # predicate zeroing
                mode |= dst_zero << SVP64MODE.DZ  # predicate zeroing
                if is_ldst:
                    # TODO: for now, LD/ST-indexed is ignored.
                    mode |= ldst_elstride << SVP64MODE.ELS_NORMAL  # el-strided
                else:
                    # TODO, reduce and subvector mode
                    # 00  1   dz CRM  reduce mode (mapreduce), SUBVL=1
                    # 00  1   SVM CRM subvector reduce mode, SUBVL>1
                    pass
                sv_mode = 0b00

            ######################################
            # ldst-immediate "post" (and "load-fault-first" modes)
            elif sv_mode == 0b00 and ldst_postinc == 1: # (or ldst_ld_ffirst)
                mode |= (0b1 << SVP64MODE.LDI_POST)         # sets bit 2
                mode |= (ldst_postinc << SVP64MODE.LDI_PI)  # sets post-inc

            ######################################
            # "mapreduce" modes
            elif sv_mode == 0b00:
                mode |= (0b1 << SVP64MODE.REDUCE)  # sets mapreduce
                assert dst_zero == 0, "dest-zero not allowed in mapreduce mode"
                if reverse_gear:
                    mode |= (0b1 << SVP64MODE.RG)  # sets Reverse-gear mode
                if mapreduce_crm:
                    mode |= (0b1 << SVP64MODE.CRM)  # sets CRM mode
                    assert rc_mode, "CRM only allowed when Rc=1"
                # bit of weird encoding to jam zero-pred or SVM mode in.
                # SVM mode can be enabled only when SUBVL=2/3/4 (vec2/3/4)
                if subvl == 0:
                    mode |= dst_zero << SVP64MODE.DZ  # predicate zeroing

            ######################################
            # "failfirst" modes
            elif failfirst is not False and not is_cr: # sv_mode == 0b01:
                assert src_zero == 0, "dest-zero not allowed in failfirst mode"
                if failfirst == 'RC1':
                    mode |= (0b1 << SVP64MODE.RC1)  # sets RC1 mode
                    mode |= (dst_zero << SVP64MODE.DZ)  # predicate dst-zeroing
                    assert rc_mode == False, "ffirst RC1 only ok when Rc=0"
                elif failfirst == '~RC1':
                    mode |= (0b1 << SVP64MODE.RC1)  # sets RC1 mode
                    mode |= (dst_zero << SVP64MODE.DZ)  # predicate dst-zeroing
                    mode |= (0b1 << SVP64MODE.INV)  # ... with inversion
                    assert rc_mode == False, "ffirst RC1 only ok when Rc=0"
                else:
                    assert dst_zero == 0, "dst-zero not allowed in ffirst BO"
                    assert rc_mode, "ffirst BO only possible when Rc=1"
                    mode |= (failfirst << SVP64MODE.BO_LSB)  # set BO

            # (crops is really different)
            elif failfirst is not False and is_cr:
                if failfirst in ['RC1', '~RC1']:
                    mode |= (src_zero << SVP64MODE.SZ)  # predicate src-zeroing
                    mode |= (dst_zero << SVP64MODE.DZ)  # predicate dst-zeroing
                    if failfirst == '~RC1':
                        mode |= (0b1 << SVP64MODE.INV)  # ... with inversion
                else:
                    assert dst_zero == src_zero, "dz must equal sz in ffirst BO"
                    mode |= (failfirst << SVP64MODE.BO_LSB)  # set BO
                    svp64_rm.cr_op.zz = dst_zero
                if vli:
                    sv_mode |= 1 # set VLI in LSB of 2-bit mode
                    #svp64_rm.cr_op.vli = 1

            ######################################
            # "saturation" modes
            elif sv_mode == 0b10:
                mode |= src_zero << SVP64MODE.SZ  # predicate zeroing
                mode |= dst_zero << SVP64MODE.DZ  # predicate zeroing
                mode |= (saturation << SVP64MODE.N)  # signed/us saturation

            ######################################
            # "predicate-result" modes.  err... code-duplication from ffirst
            elif sv_mode == 0b11:
                assert src_zero == 0, "dest-zero not allowed in predresult mode"
                if predresult == 'RC1':
                    mode |= (0b1 << SVP64MODE.RC1)  # sets RC1 mode
                    mode |= (dst_zero << SVP64MODE.DZ)  # predicate dst-zeroing
                    assert rc_mode == False, "pr-mode RC1 only ok when Rc=0"
                elif predresult == '~RC1':
                    mode |= (0b1 << SVP64MODE.RC1)  # sets RC1 mode
                    mode |= (dst_zero << SVP64MODE.DZ)  # predicate dst-zeroing
                    mode |= (0b1 << SVP64MODE.INV)  # ... with inversion
                    assert rc_mode == False, "pr-mode RC1 only ok when Rc=0"
                else:
                    assert dst_zero == 0, "dst-zero not allowed in pr-mode BO"
                    assert rc_mode, "pr-mode BO only possible when Rc=1"
                    mode |= (predresult << SVP64MODE.BO_LSB)  # set BO

        # whewww.... modes all done :)
        # now put into svp64_rm, but respect MSB0 order
        if sv_mode & 1:
            mode |= (0b1 << SVP64MODE.MOD2_LSB)
        if sv_mode & 2:
            mode |= (0b1 << SVP64MODE.MOD2_MSB)

        if sea:
            mode |= (0b1 << SVP64MODE.SEA)

        # this is a mess. really look forward to replacing it with Insn DB
        if not is_bc:
            svp64_rm.mode = mode      # mode: bits 19-23
            if vli and not is_cr:
                svp64_rm.normal.ffrc0.VLi = 1

            # put in predicate masks into svp64_rm
            if ptype == '2P':
                svp64_rm.smask = smask  # source pred: bits 16-18

            # put in elwidths unless cr
            if not is_cr:
                svp64_rm.ewsrc = srcwid    # srcwid: bits 6-7
            svp64_rm.elwidth = destwid  # destwid: bits 4-5

        svp64_rm.mmode = mmode         # mask mode: bit 0
        svp64_rm.mask = pmask          # 1-pred: bits 1-3
        svp64_rm.subvl = subvl         # and subvl: bits 8-9

        # nice debug printout. (and now for something completely different)
        # https://youtu.be/u0WOIwlXE9g?t=146
        svp64_rm_value = int(svp64_rm)
        log("svp64_rm", hex(svp64_rm_value), bin(svp64_rm_value))
        log("    mmode  0    :", bin(mmode))
        log("    pmask  1-3  :", bin(pmask))
        log("    dstwid 4-5  :", bin(destwid))
        log("    srcwid 6-7  :", bin(srcwid))
        log("    subvl  8-9  :", bin(subvl))
        log("    mode   19-23:", bin(svp64_rm.mode))
        offs = 2 if etype == 'EXTRA2' else 3  # 2 or 3 bits
        for idx, sv_extra in extras.items():
            if idx is None:
                continue
            if idx[0] == 'imm':
                continue
            srcdest, idx, duplicate = idx
            start = (10+idx*offs)
            end = start + offs-1
            log("    extra%d %2d-%2d:" % (idx, start, end),
                bin(sv_extra))
        if ptype == '2P':
            log("    smask  16-17:", bin(smask))
        log()

        # update prefix PO and ID (aka PID)
        svp64_prefix.PO = 0x1
        svp64_prefix.id = 0b11

        # fiinally yield the svp64 prefix and the thingy.  v3.0b opcode
        rc = '.' if rc_mode else ''
        yield ".long 0x%08x" % int(svp64_prefix)
        log(v30b_op, v30b_newfields)

        v30b_op_rc = v30b_op
        if not v30b_op.endswith('.'):
            v30b_op_rc += rc

        record = None
        if os.environ.get("INSNDB"):
            record = DB[opcode]
        if record is not None:
            insn = WordInstruction.assemble(db=DB,
                opcode=opcode, arguments=fields)
            yield " ".join((
                f".long 0x{int(insn):08X}",
                "#",
                opcode,
                ",".join(fields),
            ))
        else:
            if not v30b_op.endswith('.'):
                v30b_op += rc
            yield "%s %s" % (v30b_op, ", ".join(v30b_newfields))
        for (name, span) in svp64_insn.traverse("SVP64"):
            value = svp64_insn.storage[span]
            log(name, f"{value.value:0{value.bits}b}", span)
        log("new v3.0B fields", v30b_op, v30b_newfields)

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


def asm_process():
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
        record = DB[op]
        if not op.startswith('sv.') and record is None:
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
           'sv.extsw./pr=eq 5.v, 31',
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
        'maxs 3,12,5',
        'maxs. 3,12,5',
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
        "dsld 5,4,5,3",

    ]
    isa = SVP64Asm(lst, macros=macros)
    log("list:\n", "\n\t".join(list(isa)))
    # running svp64.py is designed to test hard-coded lists
    # (above) - which strictly speaking should all be unit tests.
    # if you need to actually do assembler translation at the
    # commandline use "pysvp64asm" - see setup.py
    # XXX NO. asm_process()

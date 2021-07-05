# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Funded by NLnet http://nlnet.nl

"""SVP64 OpenPOWER v3.0B assembly translator

This class takes raw svp64 assembly mnemonics (aliases excluded) and creates
an EXT001-encoded "svp64 prefix" (as a .long) followed by a v3.0B opcode.

It is very simple and straightforward, the only weirdness being the
extraction of the register information and conversion to v3.0B numbering.

Encoding format of svp64: https://libre-soc.org/openpower/sv/svp64/
Encoding format of LDST: https://libre-soc.org/openpower/sv/ldst/
Bugtracker: https://bugs.libre-soc.org/show_bug.cgi?id=578
"""

import os, sys
from collections import OrderedDict

from openpower.decoder.isa.caller import (SVP64PrefixFields, SV64P_MAJOR_SIZE,
                                    SV64P_PID_SIZE, SVP64RMFields,
                                    SVP64RM_EXTRA2_SPEC_SIZE,
                                    SVP64RM_EXTRA3_SPEC_SIZE,
                                    SVP64RM_MODE_SIZE, SVP64RM_SMASK_SIZE,
                                    SVP64RM_MMODE_SIZE, SVP64RM_MASK_SIZE,
                                    SVP64RM_SUBVL_SIZE, SVP64RM_EWSRC_SIZE,
                                    SVP64RM_ELWIDTH_SIZE)
from openpower.decoder.pseudo.pagereader import ISA
from openpower.decoder.power_svp64 import SVP64RM, get_regtype, decode_extra
from openpower.decoder.selectable_int import SelectableInt
from openpower.consts import SVP64MODE

# for debug logging
from openpower.util import log


# decode GPR into sv extra
def  get_extra_gpr(etype, regmode, field):
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
def  get_extra_cr_3bit(etype, regmode, field):
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
    pmap = { # integer
            '1<<r3': (0, 0b001),
            'r3'   : (0, 0b010),
            '~r3'   : (0, 0b011),
            'r10'   : (0, 0b100),
            '~r10'  : (0, 0b101),
            'r30'   : (0, 0b110),
            '~r30'  : (0, 0b111),
            # CR
            'lt'    : (1, 0b000),
            'nl'    : (1, 0b001), 'ge'    : (1, 0b001), # same value
            'gt'    : (1, 0b010),
            'ng'    : (1, 0b011), 'le'    : (1, 0b011), # same value
            'eq'    : (1, 0b100),
            'ne'    : (1, 0b101),
            'so'    : (1, 0b110), 'un'    : (1, 0b110), # same value
            'ns'    : (1, 0b111), 'nu'    : (1, 0b111), # same value
           }
    assert encoding in pmap, \
        "encoding %s for predicate not recognised" % encoding
    return pmap[encoding]


# decodes "Mode" in similar way to BO field (supposed to, anyway)
def decode_bo(encoding):
    pmap = { # TODO: double-check that these are the same as Branch BO
            'lt'    : 0b000,
            'nl'    : 0b001, 'ge'    : 0b001, # same value
            'gt'    : 0b010,
            'ng'    : 0b011, 'le'    : 0b011, # same value
            'eq'    : 0b100,
            'ne'    : 0b101,
            'so'    : 0b110, 'un'    : 0b110, # same value
            'ns'    : 0b111, 'nu'    : 0b111, # same value
           }
    assert encoding in pmap, \
        "encoding %s for BO Mode not recognised" % encoding
    return pmap[encoding]

# partial-decode fail-first mode
def decode_ffirst(encoding):
    if encoding in ['RC1', '~RC1']:
        return encoding
    return decode_bo(encoding)


def decode_reg(field):
    # decode the field number. "5.v" or "3.s" or "9"
    field = field.split(".")
    regmode = 'scalar' # default
    if len(field) == 2:
        if field[1] == 's':
            regmode = 'scalar'
        elif field[1] == 'v':
            regmode = 'vector'
    field = int(field[0]) # actual register number
    return field, regmode


def decode_imm(field):
    ldst_imm = "(" in field and field[-1] == ')'
    if ldst_imm:
        return field[:-1].split("(")
    else:
        return None, field


# decodes svp64 assembly listings and creates EXT001 svp64 prefixes
class SVP64Asm:
    def __init__(self, lst, bigendian=False, macros=None):
        if macros is None:
            macros = {}
        self.macros = macros
        self.lst = lst
        self.trans = self.translate(lst)
        self.isa = ISA() # reads the v3.0B pseudo-code markdown files
        self.svp64 = SVP64RM() # reads the svp64 Remap entries for registers
        assert bigendian == False, "error, bigendian not supported yet"

    def __iter__(self):
        yield from self.trans

    def translate_one(self, insn, macros=None):
        if macros is None:
            macros = {}
        macros.update(self.macros)
        isa = self.isa
        svp64 = self.svp64
        # find first space, to get opcode
        ls = insn.split(' ')
        opcode = ls[0]
        # now find opcode fields
        fields = ''.join(ls[1:]).split(',')
        mfields = list(map(str.strip, fields))
        log ("opcode, fields", ls, opcode, mfields)
        fields = []
        # macro substitution
        for field in mfields:
            fields.append(macro_subst(macros, field))
        log ("opcode, fields substed", ls, opcode, fields)

        # sigh have to do setvl here manually for now...
        if opcode in ["setvl", "setvl."]:
            insn = 22 << (31-5)          # opcode 22, bits 0-5
            fields = list(map(int, fields))
            insn |= fields[0] << (31-10) # RT       , bits 6-10
            insn |= fields[1] << (31-15) # RA       , bits 11-15
            insn |= fields[2] << (31-23) # SVi      , bits 16-23
            insn |= fields[3] << (31-24) # vs       , bit  24
            insn |= fields[4] << (31-25) # ms       , bit  25
            insn |= 0b00000   << (31-30) # XO       , bits 26..30
            if opcode == 'setvl.':
                insn |= 1 << (31-31)     # Rc=1     , bit 31
            log ("setvl", bin(insn))
            yield ".long 0x%x" % insn
            return

        # and svremap.  note that the dimension fields one subtracted from each
        if opcode == 'svremap':
            insn = 22 << (31-5)          # opcode 22, bits 0-5
            fields = list(map(int, fields))
            insn |= (fields[0]-1) << (31-10) # SVxd       , bits 6-10
            insn |= (fields[1]-1) << (31-15) # SVyd       , bits 11-15
            insn |= (fields[2]-1) << (31-16) # SVzd       , bits 16-20
            insn |= (fields[3]) << (31-21) # SVRM       , bits 21-25
            insn |= 0b00001   << (31-30) # XO       , bits 26..30
            log ("svremap", bin(insn))
            yield ".long 0x%x" % insn
            return

        # identify if is a svp64 mnemonic
        if not opcode.startswith('sv.'):
            yield insn  # unaltered
            return
        opcode = opcode[3:] # strip leading "sv"

        # start working on decoding the svp64 op: sv.basev30Bop/vec2/mode
        opmodes = opcode.split("/") # split at "/"
        v30b_op = opmodes.pop(0)    # first is the v3.0B
        # check instruction ends with dot
        rc_mode = v30b_op.endswith('.')
        if rc_mode:
            v30b_op = v30b_op[:-1]

        # sigh again, have to recognised LD/ST bit-reverse instructions
        # this has to be "processed" to fit into a v3.0B without the "br"
        # e.g. ldbr is actually ld
        ldst_bitreverse = v30b_op.startswith("l") and v30b_op.endswith("br")

        if v30b_op not in isa.instr:
            raise Exception("opcode %s of '%s' not supported" % \
                            (v30b_op, insn))

        if ldst_bitreverse:
            # okaay we need to process the fields and make this:
            #     ldbr RT, SVD(RA), RC  - 11 bits for SVD, 5 for RC
            # into this:
            #     ld RT, D(RA)          - 16 bits
            # likewise same for SVDS (9 bits for SVDS, 5 for RC, 14 bits for DS)
            form = isa.instr[v30b_op].form # get form (SVD-Form, SVDS-Form)

            newfields = []
            for field in fields:
                # identify if this is a ld/st immediate(reg) thing
                ldst_imm = "(" in field and field[-1] == ')'
                if ldst_imm:
                    newfields.append(field[:-1].split("("))
                else:
                    newfields.append(field)

            immed, RA = newfields[1]
            immed = int(immed)
            RC = int(newfields.pop(2)) # better be an integer number!
            if form == 'SVD': # 16 bit: immed 11 bits, RC shift up 11
                immed = (immed & 0b11111111111) | (RC<<11)
                if immed & (1<<15): # should be negative
                    immed -= 1<<16
            if form == 'SVDS': # 14 bit: immed 9 bits, RC shift up 9
                immed = (immed & 0b111111111) | (RC<<9)
                if immed & (1<<13): # should be negative
                    immed -= 1<<14
            newfields[1] = "%d(%s)" % (immed, RA)
            fields = newfields

            # and strip off "br" from end, and add "br" to opmodes, instead
            v30b_op = v30b_op[:-2]
            opmodes.append("br")
            log ("rewritten", v30b_op, opmodes, fields)

        if v30b_op not in svp64.instrs:
            raise Exception("opcode %s of '%s' not an svp64 instruction" % \
                            (v30b_op, insn))
        v30b_regs = isa.instr[v30b_op].regs[0] # get regs info "RT, RA, RB"
        rm = svp64.instrs[v30b_op]             # one row of the svp64 RM CSV
        log ("v3.0B op", v30b_op, "Rc=1" if rc_mode else '')
        log ("v3.0B regs", opcode, v30b_regs)
        log ("RM", rm)

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

        log ("EXTRA field index, src", svp64_src)
        log ("EXTRA field index, dest", svp64_dest)

        # okaaay now we identify the field value (opcode N,N,N) with
        # the pseudo-code info (opcode RT, RA, RB)
        assert len(fields) == len(v30b_regs), \
            "length of fields %s must match insn `%s`" % \
                    (str(v30b_regs), insn)
        opregfields = zip(fields, v30b_regs) # err that was easy

        # now for each of those find its place in the EXTRA encoding
        # note there is the possibility (for LD/ST-with-update) of
        # RA occurring **TWICE**.  to avoid it getting added to the
        # v3.0B suffix twice, we spot it as a duplicate, here
        extras = OrderedDict()
        for idx, (field, regname) in enumerate(opregfields):
            imm, regname = decode_imm(regname)
            rtype = get_regtype(regname)
            log ("    idx find", rtype, idx, field, regname, imm)
            if rtype is None:
                # probably an immediate field, append it straight
                extras[('imm', idx, False)] = (idx, field, None, None, None)
                continue
            extra = svp64_src.get(regname, None)
            if extra is not None:
                extra = ('s', extra, False) # not a duplicate
                extras[extra] = (idx, field, regname, rtype, imm)
                log ("    idx src", idx, extra, extras[extra])
            dextra = svp64_dest.get(regname, None)
            log ("regname in", regname, dextra)
            if dextra is not None:
                is_a_duplicate = extra is not None # duplicate spotted
                dextra = ('d', dextra, is_a_duplicate)
                extras[dextra] = (idx, field, regname, rtype, imm)
                log ("    idx dst", idx, extra, extras[dextra])

        # great! got the extra fields in their associated positions:
        # also we know the register type. now to create the EXTRA encodings
        etype = rm['Etype'] # Extra type: EXTRA3/EXTRA2
        ptype = rm['Ptype'] # Predication type: Twin / Single
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

            field, regmode = decode_reg(field)
            log ("    ", extra_idx, rname, rtype,
                           regmode, iname, field, end=" ")

            # see Mode field https://libre-soc.org/openpower/sv/svp64/
            # XXX TODO: the following is a bit of a laborious repeated
            # mess, which could (and should) easily be parameterised.
            # XXX also TODO: the LD/ST modes which are different
            # https://libre-soc.org/openpower/sv/ldst/

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
                        # range is r0-r127 in increments of 4
                        assert sv_extra & 0b01 == 0, \
                            "%s: vector field %s cannot fit " \
                            "into EXTRA2 %s" % \
                                (insn, rname, str(extras[extra_idx]))
                        # all good: encode as vector (bit 2 set)
                        sv_extra = 0b10 | (sv_extra >> 1)
                elif regmode == 'vector':
                    # EXTRA3 vector bit needs marking
                    sv_extra |= 0b100

            # encode SV-CR 3-bit field into extra, v3.0field
            elif rtype == 'CR_3bit':
                sv_extra, field = get_extra_cr_3bit(etype, regmode, field)
                # now sanity-check (and shrink afterwards)
                if etype == 'EXTRA2':
                    if regmode == 'scalar':
                        # range is CR0-CR15 in increments of 1
                        assert (sv_extra >> 1) == 0, \
                            "scalar CR %s cannot fit into EXTRA2 %s" % \
                                (rname, str(extras[extra_idx]))
                        # all good: encode as scalar
                        sv_extra = sv_extra & 0b01
                    else:
                        # range is CR0-CR127 in increments of 16
                        assert sv_extra & 0b111 == 0, \
                            "vector CR %s cannot fit into EXTRA2 %s" % \
                                (rname, str(extras[extra_idx]))
                        # all good: encode as vector (bit 2 set)
                        sv_extra = 0b10 | (sv_extra >> 3)
                else:
                    if regmode == 'scalar':
                        # range is CR0-CR31 in increments of 1
                        assert (sv_extra >> 2) == 0, \
                            "scalar CR %s cannot fit into EXTRA2 %s" % \
                                (rname, str(extras[extra_idx]))
                        # all good: encode as scalar
                        sv_extra = sv_extra & 0b11
                    else:
                        # range is CR0-CR127 in increments of 8
                        assert sv_extra & 0b11 == 0, \
                            "vector CR %s cannot fit into EXTRA2 %s" % \
                                (rname, str(extras[extra_idx]))
                        # all good: encode as vector (bit 3 set)
                        sv_extra = 0b100 | (sv_extra >> 2)

            # encode SV-CR 5-bit field into extra, v3.0field
            # *sigh* this is the same as 3-bit except the 2 LSBs are
            # passed through
            elif rtype == 'CR_5bit':
                cr_subfield = field & 0b11
                field = field >> 2 # strip bottom 2 bits
                sv_extra, field = get_extra_cr_3bit(etype, regmode, field)
                # now sanity-check (and shrink afterwards)
                if etype == 'EXTRA2':
                    if regmode == 'scalar':
                        # range is CR0-CR15 in increments of 1
                        assert (sv_extra >> 1) == 0, \
                            "scalar CR %s cannot fit into EXTRA2 %s" % \
                                (rname, str(extras[extra_idx]))
                        # all good: encode as scalar
                        sv_extra = sv_extra & 0b01
                    else:
                        # range is CR0-CR127 in increments of 16
                        assert sv_extra & 0b111 == 0, \
                            "vector CR %s cannot fit into EXTRA2 %s" % \
                                (rname, str(extras[extra_idx]))
                        # all good: encode as vector (bit 2 set)
                        sv_extra = 0b10 | (sv_extra >> 3)
                else:
                    if regmode == 'scalar':
                        # range is CR0-CR31 in increments of 1
                        assert (sv_extra >> 2) == 0, \
                            "scalar CR %s cannot fit into EXTRA2 %s" % \
                                (rname, str(extras[extra_idx]))
                        # all good: encode as scalar
                        sv_extra = sv_extra & 0b11
                    else:
                        # range is CR0-CR127 in increments of 8
                        assert sv_extra & 0b11 == 0, \
                            "vector CR %s cannot fit into EXTRA2 %s" % \
                                (rname, str(extras[extra_idx]))
                        # all good: encode as vector (bit 3 set)
                        sv_extra = 0b100 | (sv_extra >> 2)
                # reconstruct the actual 5-bit CR field
                field = (field << 2) | cr_subfield

            else:
                print ("no type match", rtype)

            # capture the extra field info
            log ("=>", "%5s" % bin(sv_extra), field)
            extras[extra_idx] = sv_extra

            # append altered field value to v3.0b, differs for LDST
            # note that duplicates are skipped e.g. EXTRA2 contains
            # *BOTH* s:RA *AND* d:RA which happens on LD/ST-with-update
            srcdest, idx, duplicate = extra_idx
            if duplicate: # skip adding to v3.0b fields, already added
                continue
            if ldst_imm:
                v30b_newfields.append(("%s(%s)" % (immed, str(field))))
            else:
                v30b_newfields.append(str(field))

        log ("new v3.0B fields", v30b_op, v30b_newfields)
        log ("extras", extras)

        # rright.  now we have all the info. start creating SVP64 RM
        svp64_rm = SVP64RMFields()

        # begin with EXTRA fields
        for idx, sv_extra in extras.items():
            log (idx)
            if idx is None: continue
            if idx[0] == 'imm': continue
            srcdest, idx, duplicate = idx
            if etype == 'EXTRA2':
                svp64_rm.extra2[idx].eq(
                    SelectableInt(sv_extra, SVP64RM_EXTRA2_SPEC_SIZE))
            else:
                svp64_rm.extra3[idx].eq(
                    SelectableInt(sv_extra, SVP64RM_EXTRA3_SPEC_SIZE))

        # identify if the op is a LD/ST. the "blegh" way. copied
        # from power_enums.  TODO, split the list _insns down.
        is_ld = v30b_op in [
        "lbarx", "lbz", "lbzu", "lbzux", "lbzx",            # load byte
        "ld", "ldarx", "ldbrx", "ldu", "ldux", "ldx",       # load double
        "lfs", "lfsx", "lfsu", "lfsux",                     # FP load single
        "lfd", "lfdx", "lfdu", "lfdux", "lfiwzx", "lfiwax", # FP load double
        "lha", "lharx", "lhau", "lhaux", "lhax",            # load half
        "lhbrx", "lhz", "lhzu", "lhzux", "lhzx",            # more load half
        "lwa", "lwarx", "lwaux", "lwax", "lwbrx",           # load word
        "lwz", "lwzcix", "lwzu", "lwzux", "lwzx",           # more load word
        ]
        is_st = v30b_op in [
        "stb", "stbcix", "stbcx", "stbu", "stbux", "stbx",
        "std", "stdbrx", "stdcx", "stdu", "stdux", "stdx",
        "stfs", "stfsx", "stfsu", "stfux",                  # FP store single
        "stfd", "stfdx", "stfdu", "stfdux", "stfiwx",       # FP store double
        "sth", "sthbrx", "sthcx", "sthu", "sthux", "sthx",
        "stw", "stwbrx", "stwcx", "stwu", "stwux", "stwx",
        ]
        # use this to determine if the SVP64 RM format is different.
        # see https://libre-soc.org/openpower/sv/ldst/
        is_ldst = is_ld or is_st

        # parts of svp64_rm
        mmode = 0  # bit 0
        pmask = 0  # bits 1-3
        destwid = 0 # bits 4-5
        srcwid = 0 # bits 6-7
        subvl = 0   # bits 8-9
        smask = 0 # bits 16-18 but only for twin-predication
        mode = 0 # bits 19-23

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
        mapreduce_svm = False

        predresult = False
        failfirst = False
        ldst_elstride = 0

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
            # bitreverse LD/ST
            elif encmode.startswith("br"):
                ldst_bitreverse = True
            # vec2/3/4
            elif encmode.startswith("vec"):
                subvl = decode_subvl(encmode[3:])
            # elwidth
            elif encmode.startswith("ew="):
                destwid = decode_elwidth(encmode[3:])
            elif encmode.startswith("sw="):
                srcwid = decode_elwidth(encmode[3:])
            # element-strided LD/ST
            elif encmode == 'els':
                ldst_elstride = 1
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
            elif encmode == 'sz':
                src_zero = 1
            elif encmode == 'dz':
                dst_zero = 1
            # failfirst
            elif encmode.startswith("ff="):
                assert sv_mode is None
                sv_mode = 0b01
                failfirst = decode_ffirst(encmode[3:])
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
            elif encmode == 'crm': # CR on map-reduce
                assert sv_mode is None
                sv_mode = 0b00
                mapreduce_crm = True
            elif encmode == 'svm': # sub-vector mode
                mapreduce_svm = True
            else:
                raise AssertionError("unknown encmode %s" % encmode)

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
        if mapreduce_svm:
            assert sv_mode == 0b00, "sub-vector mode in mapreduce only"
            assert subvl != 0, "sub-vector mode not possible on SUBVL=1"

        if src_zero:
            assert has_smask or mask_m_specified, \
                "src zeroing requires a source predicate"
        if dst_zero:
            assert has_pmask or mask_m_specified, \
                "dest zeroing requires a dest predicate"

        # check LDST bitreverse, only available in "normal" mode
        if is_ldst and ldst_bitreverse:
            assert sv_mode is None, \
                "LD bit-reverse cannot have modes (%s) applied" % sv_mode

        ######################################
        # "normal" mode
        if sv_mode is None:
            mode |= src_zero << SVP64MODE.SZ # predicate zeroing
            mode |= dst_zero << SVP64MODE.DZ # predicate zeroing
            if is_ldst:
                # TODO: for now, LD/ST-indexed is ignored.
                mode |= ldst_elstride << SVP64MODE.ELS_NORMAL # element-strided
                # bitreverse mode
                if ldst_bitreverse:
                    mode |= 1 << SVP64MODE.LDST_BITREV
            else:
                # TODO, reduce and subvector mode
                # 00  1   dz CRM  reduce mode (mapreduce), SUBVL=1
                # 00  1   SVM CRM subvector reduce mode, SUBVL>1
                pass
            sv_mode = 0b00

        ######################################
        # "mapreduce" modes
        elif sv_mode == 0b00:
            mode |= (0b1<<SVP64MODE.REDUCE) # sets mapreduce
            assert dst_zero == 0, "dest-zero not allowed in mapreduce mode"
            if reverse_gear:
                mode |= (0b1<<SVP64MODE.RG) # sets Reverse-gear mode
            if mapreduce_crm:
                mode |= (0b1<<SVP64MODE.CRM) # sets CRM mode
                assert rc_mode, "CRM only allowed when Rc=1"
            # bit of weird encoding to jam zero-pred or SVM mode in.
            # SVM mode can be enabled only when SUBVL=2/3/4 (vec2/3/4)
            if subvl == 0:
                mode |= dst_zero << SVP64MODE.DZ # predicate zeroing
            elif mapreduce_svm:
                mode |= (0b1<<SVP64MODE.SVM) # sets SVM mode

        ######################################
        # "failfirst" modes
        elif sv_mode == 0b01:
            assert src_zero == 0, "dest-zero not allowed in failfirst mode"
            if failfirst == 'RC1':
                mode |= (0b1<<SVP64MODE.RC1) # sets RC1 mode
                mode |= (dst_zero << SVP64MODE.DZ) # predicate dst-zeroing
                assert rc_mode==False, "ffirst RC1 only possible when Rc=0"
            elif failfirst == '~RC1':
                mode |= (0b1<<SVP64MODE.RC1) # sets RC1 mode
                mode |= (dst_zero << SVP64MODE.DZ) # predicate dst-zeroing
                mode |= (0b1<<SVP64MODE.INV) # ... with inversion
                assert rc_mode==False, "ffirst RC1 only possible when Rc=0"
            else:
                assert dst_zero == 0, "dst-zero not allowed in ffirst BO"
                assert rc_mode, "ffirst BO only possible when Rc=1"
                mode |= (failfirst << SVP64MODE.BO_LSB) # set BO

        ######################################
        # "saturation" modes
        elif sv_mode == 0b10:
            mode |= src_zero << SVP64MODE.SZ # predicate zeroing
            mode |= dst_zero << SVP64MODE.DZ # predicate zeroing
            mode |= (saturation << SVP64MODE.N) # signed/unsigned saturation

        ######################################
        # "predicate-result" modes.  err... code-duplication from ffirst
        elif sv_mode == 0b11:
            assert src_zero == 0, "dest-zero not allowed in predresult mode"
            if predresult == 'RC1':
                mode |= (0b1<<SVP64MODE.RC1) # sets RC1 mode
                mode |= (dst_zero << SVP64MODE.DZ) # predicate dst-zeroing
                assert rc_mode==False, "pr-mode RC1 only possible when Rc=0"
            elif predresult == '~RC1':
                mode |= (0b1<<SVP64MODE.RC1) # sets RC1 mode
                mode |= (dst_zero << SVP64MODE.DZ) # predicate dst-zeroing
                mode |= (0b1<<SVP64MODE.INV) # ... with inversion
                assert rc_mode==False, "pr-mode RC1 only possible when Rc=0"
            else:
                assert dst_zero == 0, "dst-zero not allowed in pr-mode BO"
                assert rc_mode, "pr-mode BO only possible when Rc=1"
                mode |= (predresult << SVP64MODE.BO_LSB) # set BO

        # whewww.... modes all done :)
        # now put into svp64_rm
        mode |= sv_mode
        # mode: bits 19-23
        svp64_rm.mode.eq(SelectableInt(mode, SVP64RM_MODE_SIZE))

        # put in predicate masks into svp64_rm
        if ptype == '2P':
            # source pred: bits 16-18
            svp64_rm.smask.eq(SelectableInt(smask, SVP64RM_SMASK_SIZE))
        # mask mode: bit 0
        svp64_rm.mmode.eq(SelectableInt(mmode, SVP64RM_MMODE_SIZE))
        # 1-pred: bits 1-3
        svp64_rm.mask.eq(SelectableInt(pmask, SVP64RM_MASK_SIZE))

        # and subvl: bits 8-9
        svp64_rm.subvl.eq(SelectableInt(subvl, SVP64RM_SUBVL_SIZE))

        # put in elwidths
        # srcwid: bits 6-7
        svp64_rm.ewsrc.eq(SelectableInt(srcwid, SVP64RM_EWSRC_SIZE))
        # destwid: bits 4-5
        svp64_rm.elwidth.eq(SelectableInt(destwid, SVP64RM_ELWIDTH_SIZE))

        # nice debug printout. (and now for something completely different)
        # https://youtu.be/u0WOIwlXE9g?t=146
        svp64_rm_value = svp64_rm.spr.value
        log ("svp64_rm", hex(svp64_rm_value), bin(svp64_rm_value))
        log ("    mmode  0    :", bin(mmode))
        log ("    pmask  1-3  :", bin(pmask))
        log ("    dstwid 4-5  :", bin(destwid))
        log ("    srcwid 6-7  :", bin(srcwid))
        log ("    subvl  8-9  :", bin(subvl))
        log ("    mode   19-23:", bin(mode))
        offs = 2 if etype == 'EXTRA2' else 3 # 2 or 3 bits
        for idx, sv_extra in extras.items():
            if idx is None: continue
            if idx[0] == 'imm': continue
            srcdest, idx, duplicate = idx
            start = (10+idx*offs)
            end = start + offs-1
            log ("    extra%d %2d-%2d:" % (idx, start, end),
                    bin(sv_extra))
        if ptype == '2P':
            log ("    smask  16-17:", bin(smask))
        log ()

        # first, construct the prefix from its subfields
        svp64_prefix = SVP64PrefixFields()
        svp64_prefix.major.eq(SelectableInt(0x1, SV64P_MAJOR_SIZE))
        svp64_prefix.pid.eq(SelectableInt(0b11, SV64P_PID_SIZE))
        svp64_prefix.rm.eq(svp64_rm.spr)

        # fiinally yield the svp64 prefix and the thingy.  v3.0b opcode
        rc = '.' if rc_mode else ''
        yield ".long 0x%x" % svp64_prefix.insn.value
        log(v30b_newfields)
        # argh, sv.fmaddso etc. need to be done manually
        if v30b_op == 'ffmadds':
            opcode = 59 << (32-6)    # bits 0..6 (MSB0)
            opcode |= int(v30b_newfields[0]) << (32-11) # FRT
            opcode |= int(v30b_newfields[1]) << (32-16) # FRA
            opcode |= int(v30b_newfields[2]) << (32-21) # FRB
            opcode |= int(v30b_newfields[3]) << (32-26) # FRC
            opcode |= 5 << (32-31)   # bits 26-30
            if rc:
                opcode |= 1  # Rc, bit 31.
            yield ".long 0x%x" % opcode
        else:
            yield "%s %s" % (v30b_op+rc, ", ".join(v30b_newfields))
        log ("new v3.0B fields", v30b_op, v30b_newfields)

    def translate(self, lst):
        for insn in lst:
            yield from self.translate_one(insn)


def macro_subst(macros, txt):
    again = True
    print ("subst", txt, macros)
    while again:
        again = False
        for macro, value in macros.items():
            if macro == txt:
                again = True
                replaced = txt.replace(macro, value)
                print ("macro", txt, "replaced", replaced, macro, value)
                txt = replaced
                continue
            toreplace = '%s.s' % macro
            if toreplace == txt:
                again = True
                replaced = txt.replace(toreplace, "%s.s" % value)
                print ("macro", txt, "replaced", replaced, toreplace, value)
                txt = replaced
                continue
            toreplace = '%s.v' % macro
            if toreplace == txt:
                again = True
                replaced = txt.replace(toreplace, "%s.v" % value)
                print ("macro", txt, "replaced", replaced, toreplace, value)
                txt = replaced
                continue
            toreplace = '(%s)' % macro
            if toreplace in txt:
                again = True
                replaced = txt.replace(toreplace, '(%s)' % value)
                print ("macro", txt, "replaced", replaced, toreplace, value)
                txt = replaced
                continue
    print ("    processed", txt)
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
        print ("pysvp64asm [infile | -] [outfile | -]")
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

    # read the line, look for "sv", process it
    macros = {} # macros which start ".set"
    isa = SVP64Asm([])
    for line in lines:
        ls = line.split("#")
        # identify macros
        op = ls[0].strip()
        if op.startswith("setvl") or op.startswith("svremap"):
            ws, line = get_ws(ls[0])
            lst = list(isa.translate_one(ls[0].strip(), macros))
            lst = '; '.join(lst)
            outfile.write("%s%s # %s\n" % (ws, lst, ls[0]))
            continue
        if ls[0].startswith(".set"):
            macro = ls[0][4:].split(",")
            macro, value = list(map(str.strip, macro))
            macros[macro] = value
        if len(ls) != 2:
            outfile.write(line)
            continue
        potential= ls[1].strip()
        if not potential.startswith("sv."):
            outfile.write(line)
            continue

        ws, line = get_ws(line)
        # SV line indentified
        lst = list(isa.translate_one(potential, macros))
        lst = '; '.join(lst)
        outfile.write("%s%s # %s\n" % (ws, lst, potential))


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
                 'setvl. 2, 3, 4, 1, 1',
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
             #'sv.lhzbr 5.v, 11(9.v), 15',
             #'sv.lwzbr 5.v, 11(9.v), 15',
             'sv.ffmadds 6.v, 2.v, 4.v, 6.v',
             'svremap 2, 2, 3, 0',
    ]
    isa = SVP64Asm(lst, macros=macros)
    print ("list", list(isa))
    csvs = SVP64RM()
    #asm_process()

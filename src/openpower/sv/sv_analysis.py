#!/usr/bin/env python2
#
# NOTE that this program is python2 compatible, please do not stop it
# from working by adding syntax that prevents that.
#
# Initial version written by lkcl Oct 2020
# This program analyses the Power 9 op codes and looks at in/out register uses
# The results are displayed:
#	https://libre-soc.org/openpower/opcode_regs_deduped/
#
# It finds .csv files in the directory isatables/
# then goes through the categories and creates svp64 CSV augmentation
# tables on a per-opcode basis
#
# NOTE: this program is effectively part of the Simple-V Specification.
# it encapsulates the relationships of what can be SVP64-encoded and
# holds all of the information on how to encode and decode SVP64.
# By auto-generating tables that go into the Simple-V Specification
# this program *is* the specification. do not be confused just because
# it is in python: if you do not understand please ask questions and
# help create patches with explanatory comments.

import argparse
import csv
import enum
import os
from os.path import dirname, join
from glob import glob
from collections import defaultdict
from collections import OrderedDict
from openpower.decoder.power_svp64 import SVP64RM
from openpower.decoder.power_enums import find_wiki_file, get_csv
from openpower.util import log


# Ignore those containing: valid test sprs
def glob_valid_csvs(root):
    def check_csv(fname):
        _, name = os.path.split(fname)
        if '-' in name:
            return False
        if 'valid' in fname:
            return False
        if 'test' in fname:
            return False
        if fname.endswith('insndb.csv'):
            return False
        if fname.endswith('sprs.csv'):
            return False
        if fname.endswith('minor_19_valid.csv'):
            return False
        if 'RM' in fname:
            return False
        return True

    yield from filter(check_csv, glob(root))


# Write an array of dictionaries to the CSV file name:
def write_csv(name, items, headers):
    file_path = find_wiki_file(name)
    with open(file_path, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(items)

# This will return True if all values are true.
# Not sure what this is about


def blank_key(row):
    # for v in row.values():
    #    if 'SPR' in v: # skip all SPRs
    #        return True
    for v in row.values():
        if v:
            return False
    return True

# General purpose registers have names like: RA, RT, R1, ...
# Floating point registers names like: FRT, FRA, FR1, ..., FRTp, ...
# Return True if field is a register


def isreg(field):
    return (field.startswith('R') or field.startswith('FR') or
            field == 'SPR')


# These are the attributes of the instructions,
# register names
keycolumns = ['unit', 'in1', 'in2', 'in3', 'out', 'CR in', 'CR out',
              ]  # don't think we need these: 'ldst len', 'rc', 'lk']

tablecols = ['unit', 'in', 'outcnt', 'CR in', 'CR out', 'imm'
             ]  # don't think we need these: 'ldst len', 'rc', 'lk']


def create_key(row):
    """ create an equivalent of a database key by which it is possible
    to easily categorise an instruction.  later this category is used
    to decide what kind of EXTRA encoding is to be done because the
    key contains the total number of input and output registers
    """
    res = OrderedDict()
    #print ("row", row)
    for key in keycolumns:
        # registers IN - special-case: count number of regs RA/RB/RC/RS
        if key in ['in1', 'in2', 'in3']:
            if 'in' not in res:
                res['in'] = 0
            if row['unit'] == 'BRANCH':  # branches must not include Vector SPRs
                continue
            if isreg(row[key]):
                res['in'] += 1

        # registers OUT
        if key == 'out':
            # If upd is 1 then increment the count of outputs
            if 'outcnt' not in res:
                res['outcnt'] = 0
            if isreg(row[key]):
                res['outcnt'] += 1
            if row['upd'] == '1':
                res['outcnt'] += 1

        # CRs (Condition Register) (CR0 .. CR7)
        if key.startswith('CR'):
            if row[key].startswith('NONE'):
                res[key] = '0'
            else:
                res[key] = '1'
            if row['comment'].startswith('cr'):
                res['crop'] = '1'
        # unit
        if key == 'unit':
            if row[key] == 'LDST':  # we care about LDST units
                res[key] = row[key]
            else:
                res[key] = 'OTHER'
        # LDST len (LoadStore length)
        if key.startswith('ldst'):
            if row[key].startswith('NONE'):
                res[key] = '0'
            else:
                res[key] = '1'
        # rc, lk
        if key in ['rc', 'lk']:
            if row[key] == 'ONE':
                res[key] = '1'
            elif row[key] == 'NONE':
                res[key] = '0'
            else:
                res[key] = 'R'
        if key == 'lk':
            res[key] = row[key]

    # Convert the numerics 'in' & 'outcnt' to strings
    res['in'] = str(res['in'])
    res['outcnt'] = str(res['outcnt'])

    # constants
    if row['in2'].startswith('CONST_'):
        res['imm'] = "1"  # row['in2'].split("_")[1]
    else:
        res['imm'] = ''

    return res

#


def dformat(d):
    res = []
    for k, v in d.items():
        res.append("%s: %s" % (k, v))
    return ' '.join(res)


def tformat(d):
    return "| " + ' | '.join(d) + " |"


def keyname(row):
    """converts a key into a readable string. anything null or zero
    is skipped, shortening the readable string
    """
    res = []
    if row['unit'] != 'OTHER':
        res.append(row['unit'])
    if row['in'] != '0':
        res.append('%sR' % row['in'])
    if row['outcnt'] != '0':
        res.append('%sW' % row['outcnt'])
    if row['CR in'] == '1' and row['CR out'] == '1':
        if 'crop' in row:
            res.append("CR=2R1W")
        else:
            res.append("CRio")
    elif row['CR in'] == '1':
        res.append("CRi")
    elif row['CR out'] == '1':
        res.append("CRo")
    elif 'imm' in row and row['imm']:
        res.append("imm")
    return '-'.join(res)


class Format(enum.Enum):
    BINUTILS = enum.auto()
    VHDL = enum.auto()

    @classmethod
    def _missing_(cls, value):
        return {
            "binutils": Format.BINUTILS,
            "vhdl": Format.VHDL,
        }[value.lower()]

    def __str__(self):
        return self.name.lower()

    def declarations(self, values, lens):
        def declaration_binutils(value, width):
            yield f"/* TODO: implement binutils declaration (value={value!r}, width={width!r}) */"

        def declaration_vhdl(value, width):
            yield f"    type sv_{value}_rom_array_t is " \
                f"array(0 to {width}) of sv_decode_rom_t;"

        for value in values:
            if value not in lens:
                todo = [f"TODO {value} (or no SVP64 augmentation)"]
                todo = self.wrap_comment(todo)
                yield from map(lambda line: f"    {line}", todo)
            else:
                width = lens[value]
                yield from {
                    Format.BINUTILS: declaration_binutils,
                    Format.VHDL: declaration_vhdl,
                }[self](value, width)

    def definitions(self, entries_svp64, fullcols):
        def definitions_vhdl():
            for (value, entries) in entries_svp64.items():
                yield ""
                yield f"    constant sv_{value}_decode_rom_array :"
                yield f"             sv_{value}_rom_array_t := ("
                yield f"        -- {'  '.join(fullcols)}"

                for (op, insn, row) in entries:
                    yield f"    {op:>13} => ({', '.join(row)}), -- {insn}"

                yield f"    {'others':>13} => sv_illegal_inst"
                yield "    );"
                yield ""

        def definitions_binutils():
            yield f"/* TODO: implement binutils definitions */"

        yield from {
            Format.BINUTILS: definitions_binutils,
            Format.VHDL: definitions_vhdl,
        }[self]()

    def wrap_comment(self, lines):
        def wrap_comment_binutils(lines):
            lines = tuple(lines)
            if len(lines) == 1:
                yield f"/* {lines[0]} */"
            else:
                yield "/*"
                yield from map(lambda line: f" * {line}", lines)
                yield " */"

        def wrap_comment_vhdl(lines):
            yield from map(lambda line: f"-- {line}", lines)

        yield from {
            Format.BINUTILS: wrap_comment_binutils,
            Format.VHDL: wrap_comment_vhdl,
        }[self](lines)


def read_csvs():
    csvs = {}
    csvs_svp64 = {}
    bykey = {}
    primarykeys = set()
    dictkeys = OrderedDict()
    immediates = {}
    insns = {}  # dictionary of CSV row, by instruction
    insn_to_csv = {}

    # Expand that (all .csv files)
    pth = find_wiki_file("*.csv")

    # Ignore those containing: valid test sprs
    for fname in glob_valid_csvs(pth):
        csvname = os.path.split(fname)[1]
        csvname_ = csvname.split(".")[0]
        # csvname is something like: minor_59.csv, fname the whole path
        csv = get_csv(fname)
        csvs[fname] = csv
        csvs_svp64[csvname_] = []
        for row in csv:
            if blank_key(row):
                continue
            #print("row", row)
            insn_name = row['comment']
            condition = row['CONDITIONS']
            # skip instructions that are not suitable
            if insn_name.startswith("l") and insn_name.endswith("br"):
                continue  # skip pseudo-alias lxxxbr
            if insn_name in ['mcrxr', 'mcrxrx', 'darn']:
                continue
            if insn_name in ['bctar', 'bcctr']:
                continue
            if 'rfid' in insn_name:
                continue
            if 'addpcis' in insn_name: # skip for now
                continue

            insns[(insn_name, condition)] = row  # accumulate csv data
            insn_to_csv[insn_name] = csvname_  # CSV file name by instruction
            dkey = create_key(row)
            key = tuple(dkey.values())
            #print("key=", key, dkey)
            dictkeys[key] = dkey
            primarykeys.add(key)
            if key not in bykey:
                bykey[key] = []
            bykey[key].append((csvname, row['opcode'], insn_name, condition,
                               row['form'].upper() + '-Form'))

            # detect immediates, collate them (useful info)
            if row['in2'].startswith('CONST_'):
                imm = row['in2'].split("_")[1]
                if key not in immediates:
                    immediates[key] = set()
                immediates[key].add(imm)

    primarykeys = list(primarykeys)
    primarykeys.sort()

    return (csvs, csvs_svp64, primarykeys, bykey, insn_to_csv, insns,
           dictkeys, immediates)


def regs_profile(insn, res):
    """get a more detailed register profile: 1st operand is RA,
    2nd is RB, etc. etc
    """
    regs = []
    for k in ['in1', 'in2', 'in3', 'out', 'CR in', 'CR out']:
        if insn[k].startswith('CONST'):
            res[k] = ''
            regs.append('')
        else:
            res[k] = insn[k]
            if insn[k] == 'RA_OR_ZERO':
                regs.append('RA')
            elif insn[k] != 'NONE':
                regs.append(insn[k])
            else:
                regs.append('')
    return regs


def extra_classifier(insn_name, value, name, res, regs):
    """extra_classifier: creates the SVP64.RM EXTRA2/3 classification.
    there is very little space (9 bits) to mark register operands
    (RT RA RB, BA BB, BFA, FRS etc.) with the "extra" information
    needed to tell if *EACH* operand (of which there can be up to five!)
    is Vectorised, and whether its numbering is extended into the
    0..127 range rather than the limited 3/5 bit of Scalar v3.0 Power ISA.

    thus begins the rather tedious but by-rote examination of EVERY
    Scalar instruction, working out how best to tell a decoder how to
    extend the registers.  EXTRA2 can have up to 4 slots (of 2 bit each)
    where due to RM.EXTRA being 9 bits, EXTRA3 can have up to 3 slots
    (of 3 bit each).  the index REGNAME says which slot the register
    named REGNAME must read its decoding from.  d: means destination,
    s: means source.  some are *shared slots* especially LDST update.
    some Rc=1 ops have the CR0/CR1 as a co-result which is also
    obviously Vectorised if the result is Vectorised.

    it is actually quite straightforward but the sheer quantity of
    Scalar Power ISA instructions made it prudent to do this in an
    intelligent way, almost by-rote, by analysing the register profiles.
    """
    # for LD/ST FP, use FRT/FRS not RT/RS, and use CR1 not CR0
    if insn_name.startswith("lf"):
        dRT = 'd:FRT'
        dCR = 'd:CR1'
    else:
        dRT = 'd:RT'
        dCR = 'd:CR0'
    if insn_name.startswith("stf"):
        sRS = 's:FRS'
        dCR = 'd:CR1'
    else:
        sRS = 's:RS'
        dCR = 'd:CR0'

    # sigh now the fun begins.  this isn't the sanest way to do it
    # but the patterns are pretty regular.  we start with the "profile"
    # because that determines how much space is available (total num
    # regs to decode) then if necessary begin apecialising either
    # by the instruction name or through more detailed register
    # profiling. example:
    #     if regs == ['RA', '', '', 'RT', '', '']:
    # is in the order in1  in2  in3 out1 out2 Rc=1

    #********
    # start with LD/ST

    if value == 'LDSTRM-2P-1S1D':
        res['Etype'] = 'EXTRA3'  # RM EXTRA3 type
        res['0'] = dRT    # RT: Rdest_EXTRA3
        res['1'] = 's:RA'  # RA: Rsrc1_EXTRA3

    elif value == 'LDSTRM-2P-1S2D':
        res['Etype'] = 'EXTRA2'  # RM EXTRA2 type
        res['0'] = dRT    # RT: Rdest_EXTRA3
        res['1'] = 'd:RA'  # RA: Rdest2_EXTRA2
        res['2'] = 's:RA'  # RA: Rsrc1_EXTRA2

    elif value == 'LDSTRM-2P-2S':
        # stw, std, sth, stb
        res['Etype'] = 'EXTRA3'  # RM EXTRA3 type
        res['0'] = sRS    # RS: Rdest1_EXTRA3
        res['1'] = 's:RA'  # RA: Rsrc1_EXTRA3

    elif value == 'LDSTRM-2P-2S1D':
        if 'st' in insn_name and 'x' not in insn_name:  # stwu/stbu etc
            res['Etype'] = 'EXTRA2'  # RM EXTRA2 type
            res['0'] = 'd:RA'  # RA: Rdest1_EXTRA2
            res['1'] = sRS    # RS: Rdsrc1_EXTRA2
            res['2'] = 's:RA'  # RA: Rsrc2_EXTRA2
        elif 'st' in insn_name and 'x' in insn_name:  # stwux
            res['Etype'] = 'EXTRA2'  # RM EXTRA2 type
            res['0'] = 'd:RA'  # RA: Rdest1_EXTRA2
            # RS: Rdest2_EXTRA2, RA: Rsrc1_EXTRA2
            res['1'] = "%s;%s" % (sRS, 's:RA')
            res['2'] = 's:RB'  # RB: Rsrc2_EXTRA2
        elif 'u' in insn_name:  # ldux etc.
            res['Etype'] = 'EXTRA2'  # RM EXTRA2 type
            res['0'] = dRT    # RT: Rdest1_EXTRA2
            res['1'] = 'd:RA'  # RA: Rdest2_EXTRA2
            res['2'] = 's:RB'  # RB: Rsrc1_EXTRA2
        else:
            res['Etype'] = 'EXTRA2'  # RM EXTRA2 type
            res['0'] = dRT     # RT: Rdest1_EXTRA2
            res['1'] = 's:RA'  # RA: Rsrc1_EXTRA2
            res['2'] = 's:RB'  # RB: Rsrc2_EXTRA2

    elif value == 'LDSTRM-2P-3S':
        res['Etype'] = 'EXTRA2'  # RM EXTRA2 type
        if 'cx' in insn_name:
            res['0'] = "%s;%s" % (sRS, dCR) # RS: Rsrc1_EXTRA2 CR0: dest
        else:
            res['0'] = sRS  # RS: Rsrc1_EXTRA2
        res['1'] = 's:RA'  # RA: Rsrc2_EXTRA2
        res['2'] = 's:RB'  # RA: Rsrc3_EXTRA2

    #**********
    # now begins,arithmetic

    elif value == 'RM-2P-1S1D':
        res['Etype'] = 'EXTRA3'  # RM EXTRA3 type
        if insn_name == 'mtspr':
            res['0'] = 'd:SPR'  # SPR: Rdest1_EXTRA3
            res['1'] = 's:RS'  # RS: Rsrc1_EXTRA3
        elif insn_name == 'mfspr':
            res['0'] = 'd:RS'  # RS: Rdest1_EXTRA3
            res['1'] = 's:SPR'  # SPR: Rsrc1_EXTRA3
        elif name == 'CRio' and insn_name == 'mcrf':
            res['0'] = 'd:BF'  # BFA: Rdest1_EXTRA3
            res['1'] = 's:BFA'  # BFA: Rsrc1_EXTRA3
        elif 'mfcr' in insn_name or 'mfocrf' in insn_name:
            res['0'] = 'd:RT'  # RT: Rdest1_EXTRA3
            res['1'] = 's:CR'  # CR: Rsrc1_EXTRA3
        elif insn_name == 'setb':
            res['0'] = 'd:RT'  # RT: Rdest1_EXTRA3
            res['1'] = 's:BFA'  # BFA: Rsrc1_EXTRA3
        elif insn_name.startswith('cmp'):  # cmpi
            res['0'] = 'd:BF'  # BF: Rdest1_EXTRA3
            res['1'] = 's:RA'  # RA: Rsrc1_EXTRA3
        elif regs == ['RA', '', '', 'RT', '', '']:
            res['0'] = 'd:RT'  # RT: Rdest1_EXTRA3
            res['1'] = 's:RA'  # RA: Rsrc1_EXTRA3
        elif regs == ['RA', '', '', 'RT', '', 'CR0']:
            res['0'] = 'd:RT;d:CR0'  # RT,CR0: Rdest1_EXTRA3
            res['1'] = 's:RA'  # RA: Rsrc1_EXTRA3
        elif (regs == ['RS', '', '', 'RA', '', 'CR0'] or
              regs == ['', '', 'RS', 'RA', '', 'CR0']):
            res['0'] = 'd:RA;d:CR0'  # RA,CR0: Rdest1_EXTRA3
            res['1'] = 's:RS'  # RS: Rsrc1_EXTRA3
        elif regs == ['RS', '', '', 'RA', '', '']:
            res['0'] = 'd:RA'  # RA: Rdest1_EXTRA3
            res['1'] = 's:RS'  # RS: Rsrc1_EXTRA3
        elif regs == ['', 'FRB', '', 'FRT', '0', 'CR1']:
            res['0'] = 'd:FRT;d:CR1'  # FRT,CR1: Rdest1_EXTRA3
            res['1'] = 's:FRA'  # FRA: Rsrc1_EXTRA3
        elif regs == ['', 'FRB', '', '', '', 'CR1']:
            res['0'] = 'd:CR1'  # CR1: Rdest1_EXTRA3
            res['1'] = 's:FRB'  # FRA: Rsrc1_EXTRA3
        elif regs == ['', 'FRB', '', '', '', 'BF']:
            res['0'] = 'd:BF'  # BF: Rdest1_EXTRA3
            res['1'] = 's:FRB'  # FRA: Rsrc1_EXTRA3
        elif regs == ['', 'FRB', '', 'FRT', '', 'CR1']:
            res['0'] = 'd:FRT;d:CR1'  # FRT,CR1: Rdest1_EXTRA3
            res['1'] = 's:FRB'  # FRB: Rsrc1_EXTRA3
        elif insn_name.startswith('bc'):
            res['0'] = 'd:BI'  # BI: Rdest1_EXTRA3
            res['1'] = 's:BI'  # BI: Rsrc1_EXTRA3
        elif insn_name == 'fishmv':
            # an overwrite instruction
            res['0'] = 'd:FRS'  # FRS: Rdest1_EXTRA3
            res['1'] = 's:FRS'  # FRS: Rsrc1_EXTRA3
        elif insn_name == 'setvl':
            res['0'] = 'd:RT'  # RT: Rdest1_EXTRA3
            res['1'] = 's:RA'  # RS: Rsrc1_EXTRA3
        else:
            res['0'] = 'TODO'
            print("regs TODO", insn_name, regs)

    elif value == 'RM-1P-2S1D':
        res['Etype'] = 'EXTRA3'  # RM EXTRA3 type
        if insn_name.startswith('cr'):
            res['0'] = 'd:BT'  # BT: Rdest1_EXTRA3
            res['1'] = 's:BA'  # BA: Rsrc1_EXTRA3
            res['2'] = 's:BB'  # BB: Rsrc2_EXTRA3
        elif regs == ['FRA', '', 'FRC', 'FRT', '', 'CR1']:
            res['0'] = 'd:FRT;d:CR1'  # FRT,CR1: Rdest1_EXTRA3
            res['1'] = 's:FRA'  # FRA: Rsrc1_EXTRA3
            res['2'] = 's:FRC'  # FRC: Rsrc1_EXTRA3
        # should be for fcmp
        elif regs == ['FRA', 'FRB', '', '', '', 'BF']:
            res['0'] = 'd:BF'  # BF: Rdest1_EXTRA3
            res['1'] = 's:FRA'  # FRA: Rsrc1_EXTRA3
            res['2'] = 's:FRB'  # FRB: Rsrc1_EXTRA3
        elif regs == ['FRA', 'FRB', '', 'FRT', '', '']:
            res['0'] = 'd:FRT'  # FRT: Rdest1_EXTRA3
            res['1'] = 's:FRA'  # FRA: Rsrc1_EXTRA3
            res['2'] = 's:FRB'  # FRB: Rsrc1_EXTRA3
        elif regs == ['FRA', 'FRB', '', 'FRT', '', 'CR1']:
            res['0'] = 'd:FRT;d:CR1'  # FRT,CR1: Rdest1_EXTRA3
            res['1'] = 's:FRA'  # FRA: Rsrc1_EXTRA3
            res['2'] = 's:FRB'  # FRB: Rsrc1_EXTRA3
        elif regs == ['FRA', 'RB', '', 'FRT', '', 'CR1']:
            res['0'] = 'd:FRT;d:CR1'  # FRT,CR1: Rdest1_EXTRA3
            res['1'] = 's:FRA'  # FRA: Rsrc1_EXTRA3
            res['2'] = 's:RB'  # RB: Rsrc1_EXTRA3
        elif name == '2R-1W' or insn_name == 'cmpb':  # cmpb
            if insn_name in ['bpermd', 'cmpb']:
                res['0'] = 'd:RA'  # RA: Rdest1_EXTRA3
                res['1'] = 's:RS'  # RS: Rsrc1_EXTRA3
            else:
                res['0'] = 'd:RT'  # RT: Rdest1_EXTRA3
                res['1'] = 's:RA'  # RA: Rsrc1_EXTRA3
            res['2'] = 's:RB'  # RB: Rsrc1_EXTRA3
        elif insn_name.startswith('cmp'):  # cmp
            res['0'] = 'd:BF'  # BF: Rdest1_EXTRA3
            res['1'] = 's:RA'  # RA: Rsrc1_EXTRA3
            res['2'] = 's:RB'  # RB: Rsrc1_EXTRA3
        elif (regs == ['', 'RB', 'RS', 'RA', '', 'CR0'] or
              regs == ['RS', 'RB', '', 'RA', '', 'CR0']):
            res['0'] = 'd:RA;d:CR0'  # RA,CR0: Rdest1_EXTRA3
            res['1'] = 's:RB'  # RB: Rsrc1_EXTRA3
            res['2'] = 's:RS'  # RS: Rsrc1_EXTRA3
        elif regs == ['RA', 'RB', '', 'RT', '', 'CR0']:
            res['0'] = 'd:RT;d:CR0'  # RT,CR0: Rdest1_EXTRA3
            res['1'] = 's:RA'  # RA: Rsrc1_EXTRA3
            res['2'] = 's:RB'  # RB: Rsrc1_EXTRA3
        elif regs == ['RA', '', 'RS', 'RA', '', 'CR0']:
            res['0'] = 'd:RA;d:CR0'  # RA,CR0: Rdest1_EXTRA3
            res['1'] = 's:RA'  # RA: Rsrc1_EXTRA3
            res['2'] = 's:RS'  # RS: Rsrc1_EXTRA3
        else:
            res['0'] = 'TODO'

    elif value == 'RM-2P-2S1D':
        res['Etype'] = 'EXTRA2'  # RM EXTRA2 type
        if insn_name.startswith('mt'):  # mtcrf
            res['0'] = 'd:CR'  # CR: Rdest1_EXTRA2
            res['1'] = 's:RS'  # RS: Rsrc1_EXTRA2
            res['2'] = 's:CR'  # CR: Rsrc2_EXTRA2
        else:
            res['0'] = 'TODO'

    elif value == 'RM-1P-3S1D':
        res['Etype'] = 'EXTRA2'  # RM EXTRA2 type
        if regs == ['RA', 'RB', 'RT', 'RT', '', 'CR0']:
            res['0'] = 'd:RT;d:CR0'  # RT,CR0: Rdest1_EXTRA2
            res['1'] = 's:RA'  # RA: Rsrc1_EXTRA2
            res['2'] = 's:RB'  # RT: Rsrc2_EXTRA2
            res['3'] = 's:RT'  # RT: Rsrc3_EXTRA2
        elif insn_name == 'isel':
            res['0'] = 'd:RT'  # RT: Rdest1_EXTRA2
            res['1'] = 's:RA'  # RA: Rsrc1_EXTRA2
            res['2'] = 's:RB'  # RT: Rsrc2_EXTRA2
            res['3'] = 's:BC'  # BC: Rsrc3_EXTRA2
        else:
            res['0'] = 'd:FRT;d:CR1'  # FRT, CR1: Rdest1_EXTRA2
            res['1'] = 's:FRA'  # FRA: Rsrc1_EXTRA2
            res['2'] = 's:FRB'  # FRB: Rsrc2_EXTRA2
            res['3'] = 's:FRC'  # FRC: Rsrc3_EXTRA2

    elif value == 'RM-1P-1D':
        res['Etype'] = 'EXTRA3'  # RM EXTRA3 type
        if insn_name == 'svstep':
            res['0'] = 'd:RT;d:CR0'  # RT,CR0: Rdest1_EXTRA3
        if insn_name == 'fmvis':
            res['0'] = 'd:FRS'  # FRS: Rdest1_EXTRA3


def process_csvs(format):

    print("# Draft SVP64 Power ISA register 'profile's")
    print('')
    print("this page is auto-generated, do not edit")
    print("created by http://libre-soc.org/openpower/sv_analysis.py")
    print('')

    (csvs, csvs_svp64, primarykeys, bykey, insn_to_csv, insns,
           dictkeys, immediates) = read_csvs()

    # mapping to old SVPrefix "Forms"
    mapsto = {'3R-1W-CRo': 'RM-1P-3S1D',
              '2R-1W-CRio': 'RM-1P-2S1D',
              '2R-1W-CRi': 'RM-1P-3S1D',
              '2R-1W-CRo': 'RM-1P-2S1D',
              '2R': 'non-SV',
              '2R-1W': 'RM-1P-2S1D',
              '1R-CRio': 'RM-2P-2S1D',
              '2R-CRio': 'RM-1P-2S1D',
              '2R-CRo': 'RM-1P-2S1D',
              '1R': 'non-SV',
              '1R-1W-CRio': 'RM-2P-1S1D',
              '1R-1W-CRo': 'RM-2P-1S1D',
              '1R-1W': 'RM-2P-1S1D',
              '1R-1W-imm': 'RM-2P-1S1D',
              '1R-CRo': 'RM-2P-1S1D',
              '1R-imm': 'RM-1P-1S',
              '1W-CRo': 'RM-1P-1D',
              '1W': 'non-SV',
              '1W-imm': 'RM-1P-1D',
              '1W-CRi': 'RM-2P-1S1D',
              'CRio': 'RM-2P-1S1D',
              'CR=2R1W': 'RM-1P-2S1D',
              'CRi': 'non-SV',
              'imm': 'non-SV',
              '': 'non-SV',
              'LDST-2R-imm': 'LDSTRM-2P-2S',
              'LDST-2R-1W-imm': 'LDSTRM-2P-2S1D',
              'LDST-2R-1W': 'LDSTRM-2P-2S1D',
              'LDST-2R-2W': 'LDSTRM-2P-2S1D',
              'LDST-1R-1W-imm': 'LDSTRM-2P-1S1D',
              'LDST-1R-2W-imm': 'LDSTRM-2P-1S2D',
              'LDST-3R': 'LDSTRM-2P-3S',
              'LDST-3R-CRo': 'LDSTRM-2P-3S',  # st*x
              'LDST-3R-1W': 'LDSTRM-2P-2S1D',  # st*x
              }
    print("# map to old SV Prefix")
    print('')
    print('|internal key | public name |')
    print('|-----        | ----------  |')
    for key in primarykeys:
        name = keyname(dictkeys[key])
        value = mapsto.get(name, "-")
        print(tformat([name, value + " "]))
    print('')
    print('')

    print("# keys")
    print('')
    print(tformat(tablecols) + " imms | name |")
    print(tformat([" - "] * (len(tablecols)+2)))

    # print out the keys and the table from which they're derived
    for key in primarykeys:
        name = keyname(dictkeys[key])
        row = tformat(dictkeys[key].values())
        imms = list(immediates.get(key, ""))
        imms.sort()
        row += " %s | " % ("/".join(imms))
        row += " %s |" % name
        print(row)
    print('')
    print('')

    # print out, by remap name, all the instructions under that category
    for key in primarykeys:
        name = keyname(dictkeys[key])
        value = mapsto.get(name, "-")
        print("## %s (%s)" % (name, value))
        print('')
        print(tformat(['CSV', 'opcode', 'asm', 'flags', 'form']))
        print(tformat(['---', '------', '---', '-----', '----']))
        rows = bykey[key]
        rows.sort()
        for row in rows:
            print(tformat(row))
        print('')
        print('')

    # for fname, csv in csvs.items():
    #    print (fname)

    # for insn, row in insns.items():
    #    print (insn, row)

    print("# svp64 remaps")
    svp64 = OrderedDict()
    # create a CSV file, per category, with SV "augmentation" info
    # XXX note: 'out2' not added here, needs to be added to CSV files
    # KEEP TRACK OF THESE https://bugs.libre-soc.org/show_bug.cgi?id=619
    csvcols = ['insn', 'mode', 'CONDITIONS', 'Ptype', 'Etype', 'SM']
    csvcols += ['0', '1', '2', '3']
    csvcols += ['in1', 'in2', 'in3', 'out', 'CR in', 'CR out']  # temporary
    for key in primarykeys:
        # get the decoded key containing row-analysis, and name/value
        dkey = dictkeys[key]
        name = keyname(dkey)
        value = mapsto.get(name, "-")
        if value == 'non-SV':
            continue

        # print out svp64 tables by category
        print("* **%s**: %s" % (name, value))

        # store csv entries by svp64 RM category
        if value not in svp64:
            svp64[value] = []

        rows = bykey[key]
        rows.sort()

        for row in rows:
            # for idx in range(len(row)):
            #    if row[idx] == 'NONE':
            #        row[idx] = ''
            # get the instruction
            #print(key, row)
            insn_name = row[2]
            condition = row[3]
            insn = insns[(insn_name, condition)]

            # start constructing svp64 CSV row
            res = OrderedDict()
            res['insn'] = insn_name
            res['CONDITIONS'] = condition
            res['Ptype'] = value.split('-')[1]  # predication type (RM-xN-xxx)
            # get whether R_xxx_EXTRAn fields are 2-bit or 3-bit
            res['Etype'] = 'EXTRA2'
            # go through each register matching to Rxxxx_EXTRAx
            for k in ['0', '1', '2', '3']:
                res[k] = ''
            # create "fake" out2 (TODO, needs to be added to CSV files)
            # KEEP TRACK HERE https://bugs.libre-soc.org/show_bug.cgi?id=619
            res['out2'] = 'NONE'
            if insn['upd'] == '1':  # LD/ST with update has RA as out2
                res['out2'] = 'RA'

            # set the SVP64 mode to NORMAL, LDST, BRANCH or CR
            crops = ['mfcr', 'mfocrf', 'mtcrf', 'mtocrf',
                    ]
            mode = 'NORMAL'
            if value.startswith('LDST'):
                if 'x' in insn_name: # Indexed detection
                    mode = 'LDST_IDX'
                else:
                    mode = 'LDST_IMM'
            elif insn_name.startswith('bc'):
                mode = 'BRANCH'
            elif insn_name.startswith('cr') or insn_name in crops:
                mode = 'CROP'
            res['mode'] = mode

            # create a register profile list (update res row as well)
            regs = regs_profile(insn, res)

            #print("regs", insn_name, regs)
            extra_classifier(insn_name, value, name, res, regs)

            # source-mask is hard to detect, it's part of RM-nn-nn.
            # to make disassembler easier, create a yes/no decision here
            # see https://libre-soc.org/openpower/sv/svp64/#extra_remap
            # MASK_SRC
            vstripped = value.replace("LDST", "")
            if vstripped in ['RM-2P-1S1D', 'RM-2P-2S',
                         'RM-2P-2S1D', 'RM-2P-1S2D', 'RM-2P-3S',
                        ]:
                res['SM'] = '0'
            else:
                res['SM'] = '0'
            # add to svp64 csvs
            # for k in ['in1', 'in2', 'in3', 'out', 'CR in', 'CR out']:
            #    del res[k]
            # if res['0'] != 'TODO':
            for k in res:
                if k == 'CONDITIONS':
                    continue
                if res[k] == 'NONE' or res[k] == '':
                    res[k] = '0'
            svp64[value].append(res)
            # also add to by-CSV version
            csv_fname = insn_to_csv[insn_name]
            csvs_svp64[csv_fname].append(res)

    print('')

    # now write out the csv files
    for value, csv in svp64.items():
        if value == '-':
            continue
            from time import sleep
            print ("WARNING, filename '-' should NOT exist. instrs missing")
            print ("TODO: fix this (and put in the bugreport number here)")
            sleep(2)
        # print out svp64 tables by category
        print("## %s" % value)
        print('')
        cols = csvcols + ['out2']
        print(tformat(cols))
        print(tformat([" - "] * (len(cols))))
        for d in csv:
            row = []
            for k in cols:
                row.append(d[k])
            print(tformat(row))
        print('')

        #csvcols = ['insn', 'Ptype', 'Etype', '0', '1', '2', '3']
        write_csv("%s.csv" % value, csv, csvcols + ['out2'])

    # okaaay, now we re-read them back in for producing microwatt SV

    # get SVP64 augmented CSV files
    svt = SVP64RM(microwatt_format=True)
    # Expand that (all .csv files)
    pth = find_wiki_file("*.csv")

    # Ignore those containing: valid test sprs
    for fname in glob_valid_csvs(pth):
        svp64_csv = svt.get_svp64_csv(fname)

    csvcols = ['insn', 'mode', 'Ptype', 'Etype', 'SM']
    csvcols += ['in1', 'in2', 'in3', 'out', 'out2', 'CR in', 'CR out']

    if format is Format.VHDL:
        # and a nice microwatt VHDL file
        file_path = find_wiki_file("sv_decode.vhdl")
    elif format is Format.BINUTILS:
        file_path = find_wiki_file("binutils.c")

    with open(file_path, 'w') as stream:
        output(format, svt, csvcols, insns, csvs_svp64, stream)


def output_autogen_disclaimer(format, stream):
    lines = (
        "this file is auto-generated, do not edit",
        "http://libre-soc.org/openpower/sv_analysis.py",
        "part of Libre-SOC, sponsored by NLnet",
    )
    for line in format.wrap_comment(lines):
        stream.write(line)
        stream.write("\n")
    stream.write("\n")


def output(format, svt, csvcols, insns, csvs_svp64, stream):
    lens = {
        'major': 63,
        'minor_4': 63,
        'minor_19': 7,
        'minor_30': 15,
        'minor_31': 1023,
        'minor_58': 63,
        'minor_59': 31,
        'minor_62': 63,
        'minor_63l': 511,
        'minor_63h': 16,
    }

    def svp64_canonicalize(item):
        (value, csv) = item
        value = value.lower().replace("-", "_")
        return (value, csv)

    csvs_svp64_canon = dict(map(svp64_canonicalize, csvs_svp64.items()))

    # disclaimer
    output_autogen_disclaimer(format, stream)

    # declarations
    for line in format.declarations(csvs_svp64_canon.keys(), lens):
        stream.write(f"{line}\n")

    # definitions
    sv_cols = ['sv_in1', 'sv_in2', 'sv_in3', 'sv_out', 'sv_out2',
               'sv_cr_in', 'sv_cr_out']
    fullcols = csvcols + sv_cols

    entries_svp64 = defaultdict(list)
    for (value, csv) in filter(lambda kv: kv[0] in lens, csvs_svp64_canon.items()):
        for entry in csv:
            insn = str(entry['insn'])
            condition = str(entry['CONDITIONS'])
            mode = str(entry['mode'])
            sventry = svt.svp64_instrs.get(insn, None)
            if sventry is not None:
                sventry['mode'] = mode
            op = insns[(insn, condition)]['opcode']
            # binary-to-vhdl-binary
            if op.startswith("0b"):
                op = "2#%s#" % op[2:]
            row = []
            for colname in csvcols[1:]:
                re = entry[colname]
                # zero replace with NONE
                if re == '0':
                    re = 'NONE'
                # 1/2 predication
                re = re.replace("1P", "P1")
                re = re.replace("2P", "P2")
                row.append(re)
            #print("sventry", sventry)
            for colname in sv_cols:
                if sventry is None:
                    re = 'NONE'
                else:
                    re = sventry[colname]
                row.append(re)
            entries_svp64[value].append((op, insn, row))

    for line in format.definitions(entries_svp64, fullcols):
        stream.write(f"{line}\n")


def main():
    import os
    os.environ['SILENCELOG'] = '1'
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--format",
                        type=Format, choices=Format, default=Format.VHDL,
                        help="format to be used (binutils or VHDL)")
    args = parser.parse_args()
    process_csvs(args.format)


if __name__ == '__main__':
    # don't do anything other than call main() here, cuz this code is bypassed
    # by the sv_analysis command created by setup.py
    main()

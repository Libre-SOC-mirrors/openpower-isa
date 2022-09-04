import pathlib
from openpower.decoder.power_enums import find_wiki_dir 
from openpower.decoder.power_insn import (Database, MarkdownDatabase,
                                          FieldsDatabase, PPCDatabase,
                                          IntegerOpcode, PatternOpcode,
                                          parse, Section, BitSel,
                                          FieldsOpcode)
root = find_wiki_dir()
root = pathlib.Path(root)
mdwndb = MarkdownDatabase()
fieldsdb = FieldsDatabase()

# create by-sections first. these will be the markdown tables
sections = {}
insns = {}
path = (root / "insndb.csv")
with open(path, "r", encoding="UTF-8") as stream:
    for section in parse(stream, Section.CSV):
        sections[str(section.path)] = section
        insns[str(section.path)] = []
for (name, section) in sections.items():
        print (name, section)

# enumerate all instructions and drop them into sections
db = Database(root)
for insn in db:
    insns[str(insn.section.path)].append(insn)
    print (insn)

def maxme(num, s):
    return s.ljust(num)

def binmaxed(num, v):
    return format(v, "0%db" % num)

# create one table
def do_table(fname, insns, section, divpoint):
    insns = insns[fname]
    section = sections[fname]
    start, end = section.bitsel.start, section.bitsel.end
    print ("start-end", start, end)
    bitlen = end-start+1
    half = divpoint
    lowermask = (1<<half)-1
    uppermask = (1<<(bitlen-half))-1
    table_entries = {}
    # debug-print all opcodes first
    opcode_per_insn = {}
    for insn in insns:
        opcodes = []
        for op in insn.ppc: # insn.ppc is a MultiPPCRecord which is a tuple
            opcodes.append(op.opcode)
        for op in opcodes:
            print ("op", insn.name, op)
        if insn.name not in opcode_per_insn:
            opcode_per_insn[insn.name] = []
        opcode_per_insn[insn.name] += opcodes

    # along the way work out the maximum length of the instruction name
    # that goes into the table.
    maxnamelen = 0

    # for every possible XO value, work out the row and column as lower and
    # upper halves, and if there is a opcode match put the instruction
    # name into that XO table_entry

    for XO in range(1<<bitlen):
        # calculate row, column
        lower = XO & lowermask
        upper = (XO>>half) & uppermask
        print ("search", XO, bin(XO), bin(lower), bin(upper))
        if upper not in table_entries: # really should use defaultdict here
            table_entries[upper] = {}
        table_entries[upper][lower] = None
        # hunt through all instructions, check XO against value/mask
        for insn in insns:
            opcode = opcode_per_insn[insn.name]
            for op in opcode:
                #print ("    search", XO, hex(key), insn.name,
                #                       hex(op.value), hex(op.mask))
                if ((op.value & op.mask) == (XO & op.mask)):
                    print ("    match", bin(XO), insn.name)
                    assert table_entries[upper][lower] is None, \
                            "entry %d %d (XO %s) should be empty "  \
                            "contains %s conflicting %s" % \
                            (lower, upper, bin(XO),
                             str(table_entries[upper][lower]),
                             insn.name)
                    table_entries[upper][lower] = insn.name
                    maxnamelen = max(maxnamelen, len(insn.name))
                    continue

    print (table_entries)
    # now got the table: print it out

    # create the markdown header. first line: |   |00|01|10|11|   |
    table = []
    line = [" "*6]
    for j in range(1<<(half)):
        hdr = binmaxed(half, j)
        line.append(maxme(maxnamelen, hdr))
    line.append(" "*6)
    table.append("|" + "|".join(line) + "|")
    # second line: |--|--|--|--|--|--|
    line = ["-"*6] + ["-"*maxnamelen] * (1<<(half)) + ["-"*6]
    table.append("|" + "|".join(line) + "|")

    # now the rows, the row number goes into first and last column
    for i in range(1<<(bitlen-half)):
        hdr = binmaxed(6, i)
        line = [hdr]
        for j in range(1<<(half)):
            line.append(maxme(maxnamelen, table_entries[i][j] or " "))
        line.append(hdr)
        table.append("|" + "|".join(line) + "|")

    print ("\n".join(table))

do_table('minor_30.csv', insns, sections, divpoint=2)
#do_table('minor_22.csv', insns, sections, divpoint=5)


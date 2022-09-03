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
        #fields = []
        #fields += [(insn.ppc.opcode.value, insn.ppc.bitsel)]
        #opcode = FieldsOpcode(fields)
        opcode = insn.ppc.opcode
        if not isinstance(opcode, list):
            opcode = [opcode]
        for op in opcode:
            print ("op", insn.name, op)
        opcode_per_insn[insn.name] = opcode

    maxnamelen = 0
    for i in range(1<<bitlen):
        # calculate row, column
        lower = i & lowermask
        upper = (i>>half) & uppermask
        print (i, bin(lower), bin(upper))
        if upper not in table_entries:
            table_entries[upper] = {}
        table_entries[upper][lower] = None
        # create an XO
        key = i
        print ("search", i, hex(key))
        # start hunting
        for insn in insns:
            opcode = opcode_per_insn[insn.name]
            for op in opcode:
                #print ("    search", i, hex(key), insn.name,
                #                       hex(op.value), hex(op.mask))
                if ((op.value & op.mask) == (key & op.mask)):
                    print ("    match", i, hex(key), insn.name)
                    assert (table_entries[upper][lower] is None,
                            "entry %d %d should be empty "
                            "contains %s conflicting %s" % \
                            (lower, upper, str(table_entries[upper][lower]),
                             insn.name))
                    table_entries[upper][lower] = insn.name
                    maxnamelen = max(maxnamelen, len(insn.name))
                    continue

    print (table_entries)
    # now got the table: print it out

    table = []
    line = [" "*half]
    for j in range(1<<(half)):
        hdr = binmaxed(half, j)
        line.append(maxme(maxnamelen, hdr))
    line.append(" "*half)
    table.append("|" + "|".join(line) + "|")
    line = ["-"*half] + ["-"*maxnamelen] * (1<<(half)) + ["-"*half]
    table.append("|" + "|".join(line) + "|")

    for i in range(1<<(bitlen-half)):
        hdr = binmaxed(half, i)
        line = [hdr]
        for j in range(1<<(half)):
            line.append(maxme(maxnamelen, table_entries[i][j] or " "))
        line.append(hdr)
        table.append("|" + "|".join(line) + "|")

    print ("\n".join(table))

do_table('minor_30.csv', insns, sections, divpoint=2)


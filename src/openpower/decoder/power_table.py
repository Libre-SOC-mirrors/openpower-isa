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

# create one table
def do_table(fname, insns, section):
    insns = insns[fname]
    section = sections[fname]
    start, end = section.bitsel.start, section.bitsel.end
    print ("start-end", start, end)
    bitlen = end-start+1
    half = bitlen // 2
    lowermask = (1<<half)-1
    uppermask = (1<<(bitlen-half))-1
    table_entries = {}
    # debug-print all opcodes first
    opcode_per_insn = {}
    for insn in insns:
        fields = []
        fields += [(insn.ppc.opcode.value, insn.section.bitsel)]
        opcode = FieldsOpcode(fields)
        if not isinstance(opcode, list):
            opcode = [opcode]
        for op in opcode:
            print ("op", insn.name, op)
        opcode_per_insn[insn.name] = opcode

    for i in range(1<<bitlen):
        # calculate row, column
        lower = i & lowermask
        upper = (i>>half) & uppermask
        print (i, bin(lower), bin(upper))
        if lower not in table_entries:
            table_entries[lower] = {}
        table_entries[lower][upper] = None
        # create an XO
        key = i << (31-end) # MSB0-order shift up by *end*
        print ("search", i, hex(key))
        # start hunting
        for insn in insns:
            opcode = opcode_per_insn[insn.name]
            for op in opcode:
                #print ("    search", i, hex(key), insn.name,
                #                       hex(op.value), hex(op.mask))
                if ((op.value & op.mask) == (key & op.mask)):
                    print ("    match", i, hex(key), insn.name)
                    assert (table_entries[lower][upper] is None,
                            "entry %d %d should be empty "
                            "contains %s conflicting %s" % \
                            (lower, upper, str(table_entries[lower][upper]),
                             insn.name))
                    table_entries[lower][upper] = insn.name
                    continue

do_table('minor_30.csv', insns, sections)


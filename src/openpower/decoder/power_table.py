import pathlib
from openpower.decoder.power_enums import find_wiki_dir 
from openpower.decoder.power_insn import (Database, MarkdownDatabase,
                                          FieldsDatabase, PPCDatabase,
                                          IntegerOpcode, PatternOpcode,
                                          parse, Section)
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

def do_table(insns, section):
    start, end = section.bitsel.start, section.bitsel.end
    print ("start-end", start, end)
    bitlen = end-start+1
    half = bitlen // 2
    xomask = ((1<<bitlen)-1) << start
    lowermask = (1<<half)-1
    uppermask = (1<<(bitlen-half))-1
    table_entries = {}
    for i in range(1<<bitlen):
        # calculate row, column
        lower = i & lowermask
        upper = (i>>half) & uppermask
        print (i, bin(lower), bin(upper))
        if lower not in table_entries:
            table_entries[lower] = {}
        table_entries[lower][upper] = i
        # create an XO
        key = i << start
        print ("search", i, hex(key))
        # start hunting
        for insn in insns:
            opcode = insn.opcode
            if not isinstance(opcode, list):
                opcode = [opcode]
            for op in opcode:
                if ((op.value & op.mask & xomask) == (key & op.mask & xomask)):
                    print ("match", i, hex(key), insn.name)

do_table(insns['minor_30.csv'], sections['minor_30.csv'])

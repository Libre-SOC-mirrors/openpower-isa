# SPDX-License-Identifier: LGPLv3+
# Funded by NLnet https://nlnet.nl/

# XXX TODO: get this into openpower/consts.py instead.
# create the layout from an auto-created Enum XERb
""" Record for XER as defined in
Power ISA v3.1B Book I section 3.2.2 page 49(75)

XER fields in MSB0:

| Bits  | Mnemonic | Description      |
|-------|----------|------------------|
| 0:31  | &nbsp;   | Reserved         |
| 32    | SO       | Summary Overflow |
| 33    | OV       | Overflow         |
| 34    | CA       | Carry            |
| 35:43 | &nbsp;   | Reserved         |
| 44    | OV32     | Overflow32       |
| 45    | CA32     | Carry32          |
| 46:56 | &nbsp;   | Reserved         |
| 57:63 | &nbsp;   | Reserved         |
"""

from nmigen import Record
from copy import deepcopy
from openpower.util import log
from openpower.decoder.selectable_int import (
    FieldSelectableInt, SelectableInt)


class XERRecord(Record):
    layout = [("Reserved1", 18),
              ("CA32", 1),
              ("OV32", 1),
              ("Reserved2", 9),
              ("CA", 1),
              ("OV", 1),
              ("SO", 1),
              ("Reserved3", 32),
              ]

    def __init__(self, name=None):
        super().__init__(name=name, layout=XERRecord.layout)


class XERState(SelectableInt):
    def __init__(self, value=0):
        SelectableInt.__init__(self, value, 64)
        self.fsi = {}
        offs = 0
        # set up sub-fields from Record layout
        self.fsi = {}
        l = deepcopy(XERRecord.layout)
        l.reverse()
        for field, width in l:
            end = offs+width
            fs = tuple(range(offs, end))
            v = FieldSelectableInt(self, fs)
            self.fsi[field] = v
            offs = end

    @property
    def SO(self):
        return self.fsi['SO']

    @SO.setter
    def SO(self, value):
        self.fsi['SO'].eq(value)

    @property
    def OV(self):
        return self.fsi['OV']

    @OV.setter
    def OV(self, value):
        self.fsi['OV'].eq(value)

    @property
    def CA(self):
        return self.fsi['CA']

    @CA.setter
    def CA(self, value):
        self.fsi['CA'].eq(value)

    @property
    def OV32(self):
        return self.fsi['OV32']

    @OV32.setter
    def OV32(self, value):
        self.fsi['OV32'].eq(value)

    @property
    def CA32(self):
        return self.fsi['CA32']

    @CA32.setter
    def CA32(self, value):
        self.fsi['CA32'].eq(value)


if __name__ == "__main__":
    from pprint import pprint
    print("XERRecord.layout:")
    pprint(XERRecord.layout)
    print("XERState.fsi:")
    pprint(XERState().fsi)

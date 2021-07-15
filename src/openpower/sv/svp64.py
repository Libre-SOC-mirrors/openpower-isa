# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Funded by NLnet http://nlnet.nl
"""SVP64 Data Structures

For full spec see https://libre-soc.org/openpower/sv/
"""

from nmigen import Record


# in nMigen, Record begins at the LSB and fills upwards
# however in OpenPOWER, numbering is MSB0.  sigh.
class SVP64Rec(Record):
    """SVP64 RM (Remap) Record.

    https://libre-soc.org/openpower/sv/svp64/

    | Field Name  | Field bits | Description                            |
    |-------------|------------|----------------------------------------|
    | MASKMODE    | `0`        | Execution (predication) Mask Kind      |
    | MASK        | `1:3`      | Execution Mask                         |
    | ELWIDTH     | `4:5`      | Element Width                          |
    | ELWIDTH_SRC | `6:7`      | Element Width for Source               |
    | SUBVL       | `8:9`      | Sub-vector length                      |
    | EXTRA       | `10:18`    | context-dependent extra                |
    | MODE        | `19:23`    | changes Vector behaviour               |
    """
    def __init__(self, name=None):
        Record.__init__(self, layout=[("mode"    , 5),
                                      ("extra"   , 9),
                                      ("subvl"   , 2),
                                      ("ewsrc"   , 2),
                                      ("elwidth" , 2),
                                      ("mask"    , 3),
                                      ("mmode"   , 1)], name=name)

    def ports(self):
        return [self.mmode, self.mask, self.elwidth, self.ewsrc,
                self.subvl, self.extra, self.mode]


options = {0b000: (0,1,2),
           0b001: (0,2,1),
           0b010: (1,0,2),
           0b011: (1,2,0),
           0b100: (2,0,1),
           0b101: (2,1,0)}
roptions = {}
for k, v in options.items():
    roptions[v] = k


# in nMigen, Record begins at the LSB and fills upwards
# however in OpenPOWER, numbering is MSB0.  sigh.
class SVP64SHAPE(Record):
    layout=[("mode"    , 2),
            ("skip"    , 2),
            ("offset"  , 4),
            ("invxyz"  , 3),
            ("permute" , 3),
            ("zdimsz"  , 6),
            ("ydimsz"  , 6),
            ("xdimsz"  , 6)]

    """SVP64 SHAPE Record.

    https://libre-soc.org/openpower/sv/remap/

    | Field Name | Field bits | Description                            |
    |------------|------------|----------------------------------------|
    | XDIMSZ     | `0:5`      | X Dimension size                       |
    | YDIMSZ     | `6:11`     | Y Dimension size                       |
    | ZDIMSZ     | `12:17`    | Z Dimension size                       |
    | PERMUTE    | `18:20`    | Permutation order (XYZ, XZY, YXZ...)   |
    | INVXYZ     | `21:23`    | Invert order of X or Y or Z            |
    | OFFSET     | `24:27`    | Adds to index after REMAP (offsets)    |
    | SKIP       | `28:29`    | Skips dimension numbered SKIP          |
    | MODE       | `30:31`    | Selects Mode: Matrix, FFT, DCT         |
    """
    def __init__(self, name=None):
        Record.__init__(self, layout=self.layout, name=name)

    @staticmethod
    def order(permute):
        return options[permute]

    @staticmethod
    def rorder(order):
        return roptions[tuple(order)]

    def ports(self):
        return [self.mode, self.skip, self.offset, self.invxyz, self.permute,
                self.zdimsz, self.ydimsz, self.xdimsz]


# in nMigen, Record begins at the LSB and fills upwards
# however in OpenPOWER, numbering is MSB0.  sigh.
class SVP64REMAP(Record):
    layout=[
            ("rsvd"  , 9),
            ("men"  , 5),
            ("mo1"    , 2),
            ("mo0"    , 2),
            ("mi2"    , 2),
            ("mi1"    , 2),
            ("mi0"    , 2),
            ]

    """SVP64 REMAP Record, for Context Propagation

    https://libre-soc.org/openpower/sv/propagation/

    | Field Name | Field bits | Description                            |
    |------------|------------|----------------------------------------|
    | MI0        | `0:1`      | 1st input register SVSHAPE(0-3) index  |
    | MI1        | `2:3`      | 2nd input register SVSHAPE(0-3) index  |
    | MI2        | `4:5`      | 3rd input register SVSHAPE(0-3) index  |
    | MO0        | `6:7`      | 1st output register SVSHAPE(0-3) index |
    | MO1        | `8:9`      | 2nd output register SVSHAPE(0-3) index |
    | MEN        | `10:14`    | enables MI0..MO1                       |
    | RESERVED   | `15:23`    | reserved                               |
    """
    def __init__(self, name=None):
        Record.__init__(self, layout=self.layout, name=name)

    @staticmethod
    def order(permute):
        return options[permute]

    @staticmethod
    def rorder(order):
        return roptions[tuple(order)]

    def ports(self):
        return [self.mi0, self.mi1, self.mi2,
                self.mo0, self.m02,
                self.men, self.rsvd
               ]


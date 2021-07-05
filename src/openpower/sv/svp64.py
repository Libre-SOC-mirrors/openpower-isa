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


# in nMigen, Record begins at the LSB and fills upwards
# however in OpenPOWER, numbering is MSB0.  sigh.
class SVP64REMAP(Record):
    """SVP64 SHAPE (REMAP) Record.

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
        Record.__init__(self, layout=[("mode"    , 2),
                                      ("skip"    , 2),
                                      ("offset"  , 4),
                                      ("invxyz"  , 3),
                                      ("permute" , 3),
                                      ("zdimsz"  , 6),
                                      ("ydimsz"  , 6),
                                      ("xdimsz"  , 6)], name=name)

    def order(self, permute):
        options = {0b000: [0,1,2],
                   0b001: [0,2,1],
                   0b010: [1,0,2],
                   0b011: [1,2,0],
                   0b100: [2,0,1],
                   0b101: [2,1,0]}
        return options[permute]

    def ports(self):
        return [self.mode, self.skip, self.offset, self.invxyz, self.permute,
                self.zdimsz, self.ydimsz, self.xdimsz]


# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Funded by NLnet http://nlnet.nl
"""SVSATE SPR Record.  actually a peer of PC (CIA/NIA) and MSR

https://libre-soc.org/openpower/sv/sprs/

| Field | Name     | Description           |
| ----- | -------- | --------------------- |
| 0:6   | maxvl    | Max Vector Length     |
| 7:13  |    vl    | Vector Length         |
| 14:20 | srcstep  | for srcstep = 0..VL-1 |
| 21:27 | dststep  | for dststep = 0..VL-1 |
| 28:29 | subvl    | Sub-vector length     |
| 30:31 | svstep   | for svstep = 0..SUBVL-1  |
| 32:33 | mi0      | REMAP RA SVSHAPE0-3    |
| 34:35 | mi1      | REMAP RB SVSHAPE0-3    |
| 36:37 | mi2      | REMAP RC SVSHAPE0-3    |
| 38:39 | mo0      | REMAP RT SVSHAPE0-3    |
| 40:41 | mo1      | REMAP EA SVSHAPE0-3    |
| 42:46 | SVme     | REMAP enable (RA-RT)  |
| 47:61 | rsvd     | reserved              |
| 62    | RMpst    | REMAP persistence     |
| 63    | vfirst   | Vertical First mode   |
"""

from nmigen import Signal, Record


# In nMigen, Record order is from LSB to MSB
# but Power ISA specs are all MSB to LSB (MSB0).
class SVSTATERec(Record):
    layout = [("vfirst", 1),
            ("RMpst", 1),
            ("rsvd", 15),
            ("SVme", 5),
            ("mo1", 2),
            ("mo0", 2),
            ("mi2", 2),
            ("mi1", 2),
            ("mi0", 2),
            ("svstep", 2),
            ("subvl", 2),
            ("dststep", 7),
            ("srcstep", 7),
            ("vl", 7),
            ("maxvl", 7),
        ]

    def __init__(self, name=None):
        super().__init__(name=name, layout=SVSTATERec.layout)

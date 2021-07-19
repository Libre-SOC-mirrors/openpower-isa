from openpower.decoder.selectable_int import (FieldSelectableInt,
                                              SelectableInt,
                                                )
from openpower.sv.svstate import SVSTATERec
import os
from copy import deepcopy
from openpower.util import log


class SVP64State(SelectableInt):
    def __init__(self, value=0):
        SelectableInt.__init__(self, value, 64)
        offs = 0
        # set up sub-fields from Record layout
        self.fsi = {}
        l = deepcopy(SVSTATERec.layout)
        l.reverse()
        for field, width in l:
            end =  offs+width
            fs = tuple(range(offs, end))
            v = FieldSelectableInt(self, fs)
            self.fsi[field] = v
            log("SVSTATE setup field", field, offs, end)
            offs = end

    @property
    def maxvl(self):
        return self.fsi['maxvl'].asint(msb0=True)

    @maxvl.setter
    def maxvl(self, value):
        self.fsi['maxvl'].eq(value)

    @property
    def vl(self):
        return self.fsi['vl'].asint(msb0=True)

    @vl.setter
    def vl(self, value):
        self.fsi['vl'].eq(value)

    @property
    def dststep(self):
        return self.fsi['dststep'].asint(msb0=True)

    @dststep.setter
    def dststep(self, value):
        self.fsi['dststep'].eq(value)

    @property
    def srcstep(self):
        return self.fsi['srcstep'].asint(msb0=True)

    @srcstep.setter
    def srcstep(self, value):
        self.fsi['srcstep'].eq(value)

    @property
    def subvl(self):
        return self.fsi['subvl'].asint(msb0=True)

    @subvl.setter
    def subvl(self, value):
        self.fsi['subvl'].eq(value)

    @property
    def mi0(self):
        return self.fsi['mi0'].asint(msb0=True)

    @mi0.setter
    def mi0(self, value):
        self.fsi['mi0'].eq(value)

    @property
    def mi1(self):
        return self.fsi['mi1'].asint(msb0=True)

    @mi1.setter
    def mi1(self, value):
        self.fsi['mi1'].eq(value)

    @property
    def mi2(self):
        return self.fsi['mi2'].asint(msb0=True)

    @mi2.setter
    def mi2(self, value):
        self.fsi['mi2'].eq(value)

    @property
    def mo0(self):
        return self.fsi['mo0'].asint(msb0=True)

    @mo0.setter
    def mo0(self, value):
        self.fsi['mo0'].eq(value)

    @property
    def mo1(self):
        return self.fsi['mo1'].asint(msb0=True)

    @mo1.setter
    def mo1(self, value):
        self.fsi['mo1'].eq(value)

    @property
    def SVme(self):
        return self.fsi['SVme'].asint(msb0=True)

    @SVme.setter
    def SVme(self, value):
        self.fsi['SVme'].eq(value)

    @property
    def vfirst(self):
        return self.fsi['vfirst'].asint(msb0=True)

    @vfirst.setter
    def vfirst(self, value):
        self.fsi['vfirst'].eq(value)

    @property
    def RMpst(self):
        return self.fsi['RMpst'].asint(msb0=True)

    @RMpst.setter
    def RMpst(self, value):
        self.fsi['RMpst'].eq(value)


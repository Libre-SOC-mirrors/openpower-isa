from openpower.decoder.selectable_int import (FieldSelectableInt, SelectableInt,
                                        selectconcat)
from openpower.decoder.isa.remapyield import iterate_indices
from openpower.decoder.isa.remap_fft_yield import iterate_butterfly_indices
from openpower.sv.svp64 import SVP64REMAP
import os
from copy import deepcopy
from openpower.util import log


class SVREMAP(SelectableInt):
    def __init__(self, value):
        SelectableInt.__init__(self, value, 32)
        offs = 0
        # set up sub-fields from Record layout
        self.fsi = {}
        l = deepcopy(SVP64REMAP.layout)
        l.reverse()
        for field, width in l:
            end =  offs+width
            fs = tuple(range(offs, end))
            v = FieldSelectableInt(self, fs)
            self.fsi[field] = v
            log("SVREMAP setup field", field, offs, end)
            offs = end

    @property
    def mi0(self):
        return self.fsi['mi0'].asint(msb0=True)

    @mi0.setter
    def mi0(self, value):
        self.fsi['mi0'].eq(mi0)

    @property
    def mi1(self):
        return self.fsi['mi1'].asint(msb0=True)

    @mi1.setter
    def mi1(self, value):
        self.fsi['mi1'].eq(mi1)

    @property
    def mi2(self):
        return self.fsi['mi2'].asint(msb0=True)

    @mi2.setter
    def mi2(self, value):
        self.fsi['mi2'].eq(mi2)

    @property
    def mo0(self):
        return self.fsi['mo0'].asint(msb0=True)

    @mo0.setter
    def mo0(self, value):
        self.fsi['mo0'].eq(mo0)

    @property
    def mo1(self):
        return self.fsi['mo1'].asint(msb0=True)

    @mo1.setter
    def mo1(self, value):
        self.fsi['mo1'].eq(mo1)

    @property
    def men(self):
        return self.fsi['men'].asint(msb0=True)

    @men.setter
    def men(self, value):
        self.fsi['men'].eq(men)


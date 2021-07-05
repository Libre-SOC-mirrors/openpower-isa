from openpower.decoder.isa.remapyield import iterate_indices
from openpower.decoder.selectable_int import (FieldSelectableInt, SelectableInt,
                                        selectconcat)
from openpower.sv.svp64 import SVP64REMAP
import os
from copy import deepcopy


class SVSHAPE(SelectableInt):
    def __init__(self, value):
        SelectableInt.__init__(self, value, 32)
        offs = 0
        # set up sub-fields from Record layout
        self.fsi = {}
        for field, width in SVP64REMAP.layout:
            v = FieldSelectableInt(self, tuple(range(offs, offs+width)))
            self.fsi[field] = v
            offs += width

    @property
    def order(self):
        permute = self.fsi['permute'].asint(msb0=True)
        return SVP64REMAP.order(permute)

    @order.setter
    def order(self, value):
        rorder = SVP64REMAP.rorder(value)
        self.fsi['permute'].eq(rorder)

    @property
    def xdimsz(self):
        return self.fsi['xdimsz'].asint(msb0=True)+1

    @xdimsz.setter
    def xdimsz(self, value):
        self.fsi['xdimsz'].eq(value-1)

    @property
    def ydimsz(self):
        return self.fsi['ydimsz'].asint(msb0=True)+1

    @ydimsz.setter
    def ydimsz(self, value):
        self.fsi['ydimsz'].eq(value-1)

    @property
    def zdimsz(self):
        return self.fsi['zdimsz'].asint(msb0=True)+1

    @zdimsz.setter
    def zdimsz(self, value):
        self.fsi['zdimsz'].eq(value-1)

    @property
    def lims(self):
        return [self.xdimsz, self.ydimsz, self.zdimsz]

    @lims.setter
    def lims(self, value):
        self.xdimsz = value[0]
        self.ydimsz = value[1]
        self.zdimsz = value[2]

    @property
    def invxyz(self):
        inv = self.fsi['invxyz'].asint(msb0=True)
        return [(inv & 0b1), (inv & 0b10) >> 1, (inv & 0b100) >> 2]

    @invxyz.setter
    def invxyz(self, value):
        self.fsi['invxyz'].eq(value[0] | (value[1]<<1) | (value[2]<<2))

    @property
    def mode(self):
        return self.fsi['mode'].asint(msb0=True)

    @mode.setter
    def mode(self, value):
        self.fsi['mode'].eq(value)

    @property
    def skip(self):
        return self.fsi['skip'].asint(msb0=True)

    @skip.setter
    def skip(self, value):
        self.fsi['skip'].eq(value)

    @property
    def offset(self):
        return self.fsi['offset'].asint(msb0=True)

    @offset.setter
    def offset(self, value):
        self.fsi['offset'].eq(value)

    def get_iterator(self):
        # create a **NEW** iterator each time this is called
        return iterate_indices(deepcopy(self))


if __name__ == '__main__':
    os.environ['SILENCELOG'] = "1"
    xdim = 3
    ydim = 2
    zdim = 1
    SVSHAPE0 = SVSHAPE(0)
    SVSHAPE0.lims = [xdim, ydim, zdim]
    SVSHAPE0.order = [1,0,2]  # experiment with different permutations, here
    SVSHAPE0.mode = 0b00
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,0,0] # inversion if desired

    VL = xdim * ydim * zdim

    for idx, new_idx in enumerate(SVSHAPE0.get_iterator()):
        if idx >= VL:
            break
        print ("%d->%d" % (idx, new_idx))


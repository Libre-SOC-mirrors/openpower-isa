"""provides convenient field mappings for SVSHAPE in different modes

the trickiest is Indexed mode which sits inside Matrix using two of
permute options to activate.

https://libre-soc.org/openpower/sv/remap
"""

from openpower.decoder.selectable_int import (FieldSelectableInt, SelectableInt,
                                        selectconcat)
from openpower.decoder.isa.remapyield import iterate_indices
from openpower.decoder.isa.remap_preduce_yield import (iterate_indices as
                                                iterate_preduce_indices)
from openpower.decoder.isa.remap_fft_yield import iterate_butterfly_indices
from openpower.decoder.isa.remap_dct_yield import (
                                iterate_dct_inner_butterfly_indices,
                                iterate_dct_inner_costable_indices,
                                iterate_dct_outer_butterfly_indices,
                                iterate_dct_inner_halfswap_loadstore)
from openpower.sv.svp64 import SVP64SHAPE
import os
from copy import deepcopy
from openpower.util import log


class SVSHAPE(SelectableInt):
    def __init__(self, value, gpr=None):
        SelectableInt.__init__(self, value, 32)
        self.gpr = gpr # for Indexed mode
        offs = 0
        # set up sub-fields from Record layout
        self.fsi = {}
        l = deepcopy(SVP64SHAPE.layout)
        l.reverse()
        for field, width in l:
            end =  offs+width
            fs = tuple(range(offs, end))
            v = FieldSelectableInt(self, fs)
            self.fsi[field] = v
            log("SVSHAPE setup field", field, offs, end)
            offs = end

    def copy(self):
        return SVSHAPE(self.value, self.gpr)

    def is_indexed(self):
        "REMAP Indexed Mode"
        return self.mode == 0b00 and self.submode2 in [0b110, 0b111]

    @property
    def submode2(self):
        return self.fsi['permute'].asint(msb0=True)

    @submode2.setter
    def submode2(self, value):
        self.fsi['permute'].eq(value)

    @property
    def order(self):
        permute = self.fsi['permute'].asint(msb0=True)
        if self.is_indexed():
            permute = (permute-0b110)*2 # xyz or yxz
        return SVP64SHAPE.order(permute)

    @order.setter
    def order(self, value):
        rorder = SVP64SHAPE.rorder(value)
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
    def svgpr(self):
        return self.fsi['zdimsz'].asint(msb0=True) << 1

    @property
    def zdimsz(self):
        z = self.fsi['zdimsz'].asint(msb0=True)+1
        if self.is_indexed():
            z = 1 # no z dimension when indexed
        return z

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
        if self.is_indexed():
            inv &= 0b011 # no 3rd z in indexed mode
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
    def elwid(self):
        return self.fsi['skip'].asint(msb0=True)

    @property
    def skip(self):
        if self.is_indexed():
            inv = self.fsi['invxyz'].asint(msb0=True)
            return (inv & 0b100) >> 2
        return self.fsi['skip'].asint(msb0=True)

    @skip.setter
    def skip(self, value):
        assert not self.is_indexed() # TODO
        self.fsi['skip'].eq(value)

    @property
    def offset(self):
        return self.fsi['offset'].asint(msb0=True)

    @offset.setter
    def offset(self, value):
        self.fsi['offset'].eq(value)

    def postprocess(self, idx, step):
        if self.mode != 0b00 or not self.is_indexed():
            return idx
        if self.gpr is None:
            return idx
        if self.xdimsz == 1 and self.ydimsz == 1:
            idx = step # no Index 1/2D reshaping, only Indexing
        ew_src = 8 << (3-int(self.elwid)) # convert to bitlength
        remap = self.gpr(self.svgpr, True, idx, ew_src).value
        log ("indexed_iterator", self.svgpr, idx, remap, ew_src)
        return remap

    def get_iterator(self):
        log ("SVSHAPE get_iterator", self.mode, self.ydimsz, self.is_indexed())
        if self.mode == 0b00:
            iterate_fn = iterate_indices
        elif self.mode == 0b10:
            iterate_fn = iterate_preduce_indices
        elif self.mode in [0b01, 0b11]:
            # further sub-selection
            if self.ydimsz == 1:
                iterate_fn = iterate_butterfly_indices
            elif self.ydimsz in [2, 4]:
                iterate_fn = iterate_dct_inner_butterfly_indices
            elif self.ydimsz == 3:
                iterate_fn = iterate_dct_outer_butterfly_indices
            elif self.ydimsz in [5, 13]:
                iterate_fn = iterate_dct_inner_costable_indices
            elif self.ydimsz in [6, 14, 15]:
                iterate_fn = iterate_dct_inner_halfswap_loadstore
        # create a **NEW** iterator each time this is called
        return iterate_fn(self.copy())


if __name__ == '__main__':
    os.environ['SILENCELOG'] = "1"
    xdim = 3
    ydim = 2000
    zdim = 1
    SVSHAPE0 = SVSHAPE(0)
    SVSHAPE0.lims = [xdim, ydim, zdim]
    SVSHAPE0.submode2 = 0b110 # yx indexed
    SVSHAPE0.mode = 0b00
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,0,1] # xy inversion (indices 0,1) , skip if desired (2)

    VL = 6 # xdim * ydim * zdim

    print ("Matrix Indexed Mode", SVSHAPE0.order, SVSHAPE0.invxyz)
    for idx, new_idx in enumerate(SVSHAPE0.get_iterator()):
        if idx >= VL:
            break
        print ("%d->%s" % (idx, repr(new_idx)))

    print ("")

    xdim = 3
    ydim = 2
    zdim = 1
    SVSHAPE0 = SVSHAPE(0)
    SVSHAPE0.lims = [xdim, ydim, zdim]
    SVSHAPE0.order = [1,0,2]  # experiment with different permutations, here
    SVSHAPE0.mode = 0b00
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,1,0] # inversion if desired

    VL = xdim * ydim * zdim

    print ("Matrix Mode")
    for idx, new_idx in enumerate(SVSHAPE0.get_iterator()):
        if idx >= VL:
            break
        print ("%d->%s" % (idx, repr(new_idx)))

    print ("")
    print ("FFT Mode")

    # set the dimension sizes here
    xdim = 8
    ydim = 0 # not needed
    zdim = 0 # again, not needed

    # set total. err don't know how to calculate how many there are...
    # do it manually for now

    VL = 0
    size = 2
    n = xdim
    while size <= n:
        halfsize = size // 2
        tablestep = n // size
        for i in range(0, n, size):
            for j in range(i, i + halfsize):
                VL += 1
        size *= 2

    # j schedule
    SVSHAPE0 = SVSHAPE(0)
    SVSHAPE0.lims = [xdim, ydim, zdim]
    SVSHAPE0.order = [0,1,2]  # experiment with different permutations, here
    SVSHAPE0.mode = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE(0)
    SVSHAPE1.lims = [xdim, ydim, zdim]
    SVSHAPE1.order = [0,1,2]  # experiment with different permutations, here
    SVSHAPE1.mode = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [0,0,0] # inversion if desired
    # k schedule
    SVSHAPE2 = SVSHAPE(0)
    SVSHAPE2.lims = [xdim, ydim, zdim]
    SVSHAPE2.order = [0,1,2]  # experiment with different permutations, here
    SVSHAPE2.mode = 0b10
    SVSHAPE2.offset = 0       # experiment with different offset, here
    SVSHAPE2.invxyz = [0,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    schedule = []
    for idx, (jl, jh, k) in enumerate(zip(iterate_indices(SVSHAPE0),
                                          iterate_indices(SVSHAPE1),
                                          iterate_indices(SVSHAPE2))):
        if idx >= VL:
            break
        schedule.append((jl[0], jh[0], k[0]))

    # ok now pretty-print the results, with some debug output
    size = 2
    idx = 0
    while size <= n:
        halfsize = size // 2
        tablestep = n // size
        print ("size %d halfsize %d tablestep %d" % \
                (size, halfsize, tablestep))
        for i in range(0, n, size):
            prefix = "i %d\t" % i
            k = 0
            for j in range(i, i + halfsize):
                jl, jh, ks = schedule[idx]
                print ("  %-3d\t%s j=%-2d jh=%-2d k=%-2d -> "
                        "j[jl=%-2d] j[jh=%-2d] exptable[k=%d]" % \
                                (idx, prefix, j, j+halfsize, k,
                                      jl, jh, ks))
                k += tablestep
                idx += 1
        size *= 2


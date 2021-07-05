# a "yield" version of the REMAP algorithm. a little easier to read
# than the Finite State Machine version

# python "yield" can be iterated. use this to make it clear how
# the indices are generated by using natural-looking nested loops
def iterate_indices(SVSHAPE):
    # get indices to iterate over, in the required order
    xd = SVSHAPE.lims[0]
    yd = SVSHAPE.lims[1]
    zd = SVSHAPE.lims[2]
    # create lists of indices to iterate over in each dimension
    x_r = list(range(xd))
    y_r = list(range(yd))
    z_r = list(range(zd))
    # invert the indices if needed
    if SVSHAPE.invxyz[0]: x_r.reverse()
    if SVSHAPE.invxyz[1]: y_r.reverse()
    if SVSHAPE.invxyz[2]: z_r.reverse()
    # start an infinite (wrapping) loop
    while True:
        for z in z_r:   # loop over 1st order dimension
            for y in y_r:       # loop over 2nd order dimension
                for x in x_r:           # loop over 3rd order dimension
                    # ok work out which order to construct things in.
                    # start by creating a list of tuples of the dimension
                    # and its limit
                    vals = [(SVSHAPE.lims[0], x, "x"),
                            (SVSHAPE.lims[1], y, "y"),
                            (SVSHAPE.lims[2], z, "z")
                           ]
                    # now select those by order.  this allows us to
                    # create schedules for [z][x], [x][y], or [y][z]
                    # for matrix multiply.
                    vals = [vals[SVSHAPE.order[0]],
                            vals[SVSHAPE.order[1]],
                            vals[SVSHAPE.order[2]]
                           ]
                    # some of the dimensions can be "skipped".  the order
                    # was actually selected above on all 3 dimensions,
                    # e.g. [z][x][y] or [y][z][x].  "skip" allows one of
                    # those to be knocked out
                    if SVSHAPE.skip == 0b00:
                        select = 0b111
                    elif SVSHAPE.skip == 0b11:
                        select = 0b011
                    elif SVSHAPE.skip == 0b01:
                        select = 0b110
                    elif SVSHAPE.skip == 0b10:
                        select = 0b101
                    else:
                        select = 0b111
                    result = 0
                    mult = 1
                    # ok now we can construct the result, using bits of
                    # "order" to say which ones get stacked on
                    for i in range(3):
                        lim, idx, dbg = vals[i]
                        if select & (1<<i):
                            #print ("select %d %s" % (i, dbg))
                            idx *= mult   # shifts up by previous dimension(s)
                            result += idx # adds on this dimension
                            mult *= lim   # for the next dimension

                    yield result + SVSHAPE.offset

def demo():
    # set the dimension sizes here
    xdim = 3
    ydim = 2
    zdim = 1

    # set total (can repeat, e.g. VL=x*y*z*4)
    VL = xdim * ydim * zdim

    # set up an SVSHAPE
    class SVSHAPE:
        pass
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, ydim, zdim]
    SVSHAPE0.order = [1,0,2]  # experiment with different permutations, here
    SVSHAPE0.mode = 0b00
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    for idx, new_idx in enumerate(iterate_indices(SVSHAPE0)):
        if idx >= VL:
            break
        print ("%d->%d" % (idx, new_idx))

# run the demo
if __name__ == '__main__':
    demo()

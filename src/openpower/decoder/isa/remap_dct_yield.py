# DCT "REMAP" scheduler
#
# Modifications made to create an in-place iterative DCT:
# Copyright (c) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
#
# SPDX: LGPLv3+
#
# Original fastdctlee.py by Nayuki:
# Copyright (c) 2020 Project Nayuki. (MIT License)
# https://www.nayuki.io/page/fast-discrete-cosine-transform-algorithms

import math

# bits of the integer 'val'.
def reverse_bits(val, width):
    result = 0
    for _ in range(width):
        result = (result << 1) | (val & 1)
        val >>= 1
    return result


# iterative version of [recursively-applied] half-rev.
# relies on the list lengths being power-of-two and the fact
# that bit-inversion of a list of binary numbers is the same
# as reversing the order of the list
# this version is dead easy to implement in hardware.
# a big surprise is that the half-reversal can be done with
# such a simple XOR. the inverse operation is slightly trickier
def halfrev2(vec, pre_rev=True):
    res = []
    for i in range(len(vec)):
        if pre_rev:
            res.append(i ^ (i>>1))
        else:
            ri = i
            bl = i.bit_length()
            for ji in range(1, bl):
                ri ^= (i >> ji)
            res.append(vec[ri])
    return res


# python "yield" can be iterated. use this to make it clear how
# the indices are generated by using natural-looking nested loops
def iterate_dct_inner_costable_indices(SVSHAPE):
    # get indices to iterate over, in the required order
    n = SVSHAPE.lims[0]
    mode = SVSHAPE.lims[1]
    print ("inner costable", mode)
    # creating lists of indices to iterate over in each dimension
    # has to be done dynamically, because it depends on the size
    # first, the size-based loop (which can be done statically)
    x_r = []
    size = 2
    while size <= n:
        x_r.append(size)
        size *= 2
    # invert order if requested
    if SVSHAPE.invxyz[0]:
        x_r.reverse()

    if len(x_r) == 0:
        return

    #print ("ri", ri)
    #print ("ji", ji)

    # start an infinite (wrapping) loop
    skip = 0
    z_end = 1 # doesn't exist in this, only 2 loops
    k = 0
    while True:
        for size in x_r:           # loop over 3rd order dimension (size)
            x_end = size == x_r[-1]
            # y_r schedule depends on size
            halfsize = size // 2
            y_r = []
            for i in range(0, n, size):
                y_r.append(i)
            # invert if requested
            if SVSHAPE.invxyz[1]: y_r.reverse()
            # two lists of half-range indices, e.g. j 0123, jr 7654
            j = list(range(0, halfsize))
            # invert if requested
            if SVSHAPE.invxyz[2]: j_r.reverse()
            #print ("xform jr", jr)
            # loop over 1st order dimension
            for ci, jl in enumerate(j):
                y_end = jl == j[-1]
                # now depending on MODE return the index.  inner butterfly
                if SVSHAPE.skip == 0b00: # in [0b00, 0b10]:
                    result = k  # offset into COS table
                elif SVSHAPE.skip == 0b10: #
                    result = ci # coefficient helper
                elif SVSHAPE.skip == 0b11: #
                    result = size # coefficient helper
                loopends = (z_end |
                           ((y_end and z_end)<<1) |
                            ((y_end and x_end and z_end)<<2))

                yield result + SVSHAPE.offset, loopends
                k += 1

# python "yield" can be iterated. use this to make it clear how
# the indices are generated by using natural-looking nested loops
def iterate_dct_inner_butterfly_indices(SVSHAPE):
    # get indices to iterate over, in the required order
    n = SVSHAPE.lims[0]
    mode = SVSHAPE.lims[1]
    #print ("inner butterfly", mode, SVSHAPE.skip)
    # creating lists of indices to iterate over in each dimension
    # has to be done dynamically, because it depends on the size
    # first, the size-based loop (which can be done statically)
    x_r = []
    size = 2
    while size <= n:
        x_r.append(size)
        size *= 2
    # invert order if requested
    if SVSHAPE.invxyz[0]:
        x_r.reverse()

    if len(x_r) == 0:
        return

    # reference (read/write) the in-place data in *reverse-bit-order*
    ri = list(range(n))
    if SVSHAPE.submode2 == 0b01:
        levels = n.bit_length() - 1
        ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    # reference list for not needing to do data-swaps, just swap what
    # *indices* are referenced (two levels of indirection at the moment)
    # pre-reverse the data-swap list so that it *ends up* in the order 0123..
    ji = list(range(n))
    inplace_mode = SVSHAPE.submode2 == 0b01
    #                     and SVSHAPE.skip not in [0b10, 0b11]
    if inplace_mode:
        #print ("inplace mode")
        ji = halfrev2(ji, True)

    #print ("ri", ri)
    #print ("ji", ji)

    # start an infinite (wrapping) loop
    skip = 0
    k = 0
    k_start = 0
    while True:
        for size in x_r:           # loop over 3rd order dimension (size)
            x_end = size == x_r[-1]
            # y_r schedule depends on size
            halfsize = size // 2
            y_r = []
            for i in range(0, n, size):
                y_r.append(i)
            # invert if requested
            if SVSHAPE.invxyz[1]: y_r.reverse()
            for i in y_r:       # loop over 2nd order dimension
                y_end = i == y_r[-1]
                # two lists of half-range indices, e.g. j 0123, jr 7654
                j = list(range(i, i + halfsize))
                jr = list(range(i+halfsize, i + size))
                jr.reverse()
                # invert if requested
                if SVSHAPE.invxyz[2]: j_r.reverse()
                hz2 = halfsize // 2 # zero stops reversing 1-item lists
                # if you *really* want to do the in-place swapping manually,
                # this allows you to do it.  good luck...
                if SVSHAPE.submode2 == 0b01 and not inplace_mode:
                    #print ("swap mode")
                    jr = j_r[:hz2]
                #print ("xform jr", jr)
                # loop over 1st order dimension
                k = k_start
                for ci, (jl, jh) in enumerate(zip(j, jr)):
                    z_end = jl == j[-1]
                    # now depending on MODE return the index.  inner butterfly
                    if SVSHAPE.skip == 0b00: # in [0b00, 0b10]:
                        result = ri[ji[jl]]        # lower half
                    elif SVSHAPE.skip == 0b01: # in [0b01, 0b11]:
                        result = ri[ji[jh]] # upper half
                    elif mode == 4:
                        # COS table pre-generated mode
                        if SVSHAPE.skip == 0b10: #
                            result = k # cos table offset
                    else: # mode 2
                        # COS table generated on-demand ("Vertical-First") mode
                        if SVSHAPE.skip == 0b10: #
                            result = ci # coefficient helper
                        elif SVSHAPE.skip == 0b11: #
                            result = size # coefficient helper
                    loopends = (z_end |
                               ((y_end and z_end)<<1) |
                                ((y_end and x_end and z_end)<<2))

                    yield result + SVSHAPE.offset, loopends
                    k += 1

                # now in-place swap
                if inplace_mode:
                    for ci, (jl, jh) in enumerate(zip(j[:hz2], jr[:hz2])):
                        jlh = jl+halfsize
                        #print ("inplace swap", jh, jlh)
                        tmp1, tmp2 = ji[jlh], ji[jh]
                        ji[jlh], ji[jh] = tmp2, tmp1

            # new k_start point for cos tables( runs inside x_r loop NOT i loop)
            k_start += halfsize


# python "yield" can be iterated. use this to make it clear how
# the indices are generated by using natural-looking nested loops
def iterate_dct_outer_butterfly_indices(SVSHAPE):
    # get indices to iterate over, in the required order
    n = SVSHAPE.lims[0]
    mode = SVSHAPE.lims[1]
    # createing lists of indices to iterate over in each dimension
    # has to be done dynamically, because it depends on the size
    # first, the size-based loop (which can be done statically)
    x_r = []
    size = n // 2
    while size >= 2:
        x_r.append(size)
        size //= 2
    # invert order if requested
    if SVSHAPE.invxyz[0]:
        x_r.reverse()

    if len(x_r) == 0:
        return

    #print ("outer butterfly")

    # reference (read/write) the in-place data in *reverse-bit-order*
    ri = list(range(n))
    if SVSHAPE.submode2 == 0b11:
        levels = n.bit_length() - 1
        ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    # reference list for not needing to do data-swaps, just swap what
    # *indices* are referenced (two levels of indirection at the moment)
    # pre-reverse the data-swap list so that it *ends up* in the order 0123..
    ji = list(range(n))
    inplace_mode = False # need the space... SVSHAPE.skip in [0b10, 0b11]
    if inplace_mode:
        #print ("inplace mode", SVSHAPE.skip)
        ji = halfrev2(ji, True)

    #print ("ri", ri)
    #print ("ji", ji)

    # start an infinite (wrapping) loop
    skip = 0
    k = 0
    k_start = 0
    while True:
        for size in x_r:           # loop over 3rd order dimension (size)
            halfsize = size//2
            x_end = size == x_r[-1]
            y_r = list(range(0, halfsize))
            #print ("itersum", halfsize, size, y_r)
            # invert if requested
            if SVSHAPE.invxyz[1]: y_r.reverse()
            for i in y_r:       # loop over 2nd order dimension
                y_end = i == y_r[-1]
                # one list to create iterative-sum schedule
                jr = list(range(i+halfsize, i+n-halfsize, size))
                #print ("itersum     jr", i+halfsize, i+size, jr)
                # invert if requested
                if SVSHAPE.invxyz[2]: j_r.reverse()
                hz2 = halfsize // 2 # zero stops reversing 1-item lists
                k = k_start
                for ci, jh in enumerate(jr):   # loop over 1st order dimension
                    z_end = jh == jr[-1]
                    #print ("     itersum", size, i, jh, jh+size)
                    if mode == 4:
                        # COS table pre-generated mode
                        if SVSHAPE.skip == 0b00: # in [0b00, 0b10]:
                            result = ri[ji[jh]]        # lower half
                        elif SVSHAPE.skip == 0b01: # in [0b01, 0b11]:
                            result = ri[ji[jh+size]] # upper half
                        elif SVSHAPE.skip == 0b10: #
                            result = k # cos table offset
                    else:
                        # COS table generated on-demand ("Vertical-First") mode
                        if SVSHAPE.skip == 0b00: # in [0b00, 0b10]:
                            result = ri[ji[jh]]        # lower half
                        elif SVSHAPE.skip == 0b01: # in [0b01, 0b11]:
                            result = ri[ji[jh+size]] # upper half
                        elif SVSHAPE.skip == 0b10: #
                            result = ci # coefficient helper
                        elif SVSHAPE.skip == 0b11: #
                            result = size # coefficient helper
                    loopends = (z_end |
                               ((y_end and z_end)<<1) |
                                ((y_end and x_end and z_end)<<2))

                    yield result + SVSHAPE.offset, loopends
                    k += 1

                # now in-place swap
                if SVSHAPE.submode2 == 0b11 and inplace_mode:
                    j = list(range(i, i + halfsize))
                    jr = list(range(i+halfsize, i + size))
                    jr.reverse()
                    for ci, (jl, jh) in enumerate(zip(j[:hz2], jr[:hz2])):
                        jlh = jl+halfsize
                        #print ("inplace swap", jh, jlh)
                        tmp1, tmp2 = ji[jlh], ji[jh]
                        ji[jlh], ji[jh] = tmp2, tmp1

            # new k_start point for cos tables( runs inside x_r loop NOT i loop)
            k_start += halfsize


def pprint_schedule(schedule, n):
    size = 2
    idx = 0
    while size <= n:
        halfsize = size // 2
        tablestep = n // size
        print ("size %d halfsize %d tablestep %d" % \
                (size, halfsize, tablestep))
        for i in range(0, n, size):
            prefix = "i %d\t" % i
            for j in range(i, i + halfsize):
                (jl, je), (jh, he) = schedule[idx]
                print ("  %-3d\t%s j=%-2d jh=%-2d "
                        "j[jl=%-2d] j[jh=%-2d]" % \
                                (idx, prefix, j, j+halfsize,
                                      jl, jh,
                                ),
                                "end", bin(je)[2:], bin(je)[2:])
                idx += 1
        size *= 2

def pprint_schedule_outer(schedule, n):
    size = 2
    idx = 0
    while size <= n//2:
        halfsize = size // 2
        tablestep = n // size
        print ("size %d halfsize %d tablestep %d" % \
                (size, halfsize, tablestep))
        y_r = list(range(0, halfsize))
        for i in y_r:
            prefix = "i %d\t" % i
            jr = list(range(i+halfsize, i+n-halfsize, size))
            for j in jr:
                (jl, je), (jh, he) = schedule[idx]
                print ("  %-3d\t%s j=%-2d jh=%-2d "
                        "j[jl=%-2d] j[jh=%-2d]" % \
                                (idx, prefix, j, j+halfsize,
                                      jl, jh,
                                ),
                                "end", bin(je)[2:], bin(je)[2:])
                idx += 1
        size *= 2


# totally cool *in-place* DCT algorithm using yield REMAPs
def transform2(vec):

    # Initialization
    n = len(vec)
    print ()
    print ("transform2", n)
    levels = n.bit_length() - 1

    # set up dims
    xdim = n

    # reference (read/write) the in-place data in *reverse-bit-order*
    ri = list(range(n))
    ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    # and pretend we LDed data in half-swapped *and* bit-reversed order as well
    # TODO: merge these two
    vec = halfrev2(vec, False)
    vec = [vec[ri[i]] for i in range(n)]

    # create a cos table: not strictly necessary but here for illustrative
    # purposes, to demonstrate the point that it really *is* iterative.
    # this table could be cached and used multiple times rather than
    # computed every time.
    ctable = []
    size = n
    while size >= 2:
        halfsize = size // 2
        for ci in range(halfsize):
            coeff = (math.cos((ci + 0.5) * math.pi / size) * 2.0)
            ctable.append(coeff)
            print ("coeff", size,  "ci", ci, "k", len(ctable)-1,
                   "i/n", (ci+0.5)/size, coeff)
        size //= 2

    # set up an SVSHAPE
    class SVSHAPE:
        pass
    # ci schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, 4, 0]
    SVSHAPE0.mode = 0b01
    SVSHAPE0.submode2 = 0b01
    SVSHAPE0.skip = 0b10
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [1,0,0] # inversion if desired
    # size schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, 4, 0]
    SVSHAPE1.mode = 0b01
    SVSHAPE1.submode2 = 0b01
    SVSHAPE1.skip = 0b11
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [1,0,0] # inversion if desired
    # k schedule
    SVSHAPE2 = SVSHAPE()
    SVSHAPE2.lims = [xdim, 4, 0]
    SVSHAPE2.mode = 0b01
    SVSHAPE2.submode2 = 0b01
    SVSHAPE2.skip = 0b00
    SVSHAPE2.offset = 0       # experiment with different offset, here
    SVSHAPE2.invxyz = [1,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    i0 = iterate_dct_inner_costable_indices(SVSHAPE0)
    i1 = iterate_dct_inner_costable_indices(SVSHAPE1)
    i2 = iterate_dct_inner_costable_indices(SVSHAPE2)
    for ((ci, cie), (size, sze), (k, ke)) in \
                zip(i0, i1, i2):
        print ("xform2 cos", ci, size, k)
        coeff = (math.cos((ci + 0.5) * math.pi / size) * 2.0)
        assert coeff == ctable[k]
        print ("coeff", size,  "ci", ci, "k", k,
               "i/n", (ci+0.5)/size, coeff, 
                "end", bin(cie), bin(sze), bin(ke))
        if cie == 0b111: # all loops end
            break

    ################
    # INNER butterfly
    ################

    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, 0b000001, 0]
    SVSHAPE0.mode = 0b01
    SVSHAPE0.submode2 = 0b01
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [1,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, 0b000001, 0]
    SVSHAPE1.mode = 0b01
    SVSHAPE1.submode2 = 0b01
    SVSHAPE1.skip = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [1,0,0] # inversion if desired
    # ci schedule
    SVSHAPE2 = SVSHAPE()
    SVSHAPE2.lims = [xdim, 0b000001, 0]
    SVSHAPE2.mode = 0b01
    SVSHAPE2.submode2 = 0b01
    SVSHAPE2.skip = 0b10
    SVSHAPE2.offset = 0       # experiment with different offset, here
    SVSHAPE2.invxyz = [1,0,0] # inversion if desired
    # size schedule
    SVSHAPE3 = SVSHAPE()
    SVSHAPE3.lims = [xdim, 0b000001, 0]
    SVSHAPE3.mode = 0b01
    SVSHAPE3.submode2 = 0b01
    SVSHAPE3.skip = 0b11
    SVSHAPE3.offset = 0       # experiment with different offset, here
    SVSHAPE3.invxyz = [1,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    i0 = iterate_dct_inner_butterfly_indices(SVSHAPE0)
    i1 = iterate_dct_inner_butterfly_indices(SVSHAPE1)
    i2 = iterate_dct_inner_butterfly_indices(SVSHAPE2)
    i3 = iterate_dct_inner_butterfly_indices(SVSHAPE3)
    for k, ((jl, jle), (jh, jhe), (ci, cie), (size, sze)) in \
                enumerate(zip(i0, i1, i2, i3)):
        t1, t2 = vec[jl], vec[jh]
        print ("xform2", jl, jh, ci, size)
        coeff = (math.cos((ci + 0.5) * math.pi / size) * 2.0)
        #assert coeff == ctable[k]
        vec[jl] = t1 + t2
        vec[jh] = (t1 - t2) * (1/coeff)
        print ("coeff", size, "ci", ci,
                "jl", jl, "jh", jh,
               "i/n", (ci+0.5)/size, coeff, vec[jl],
                                            vec[jh],
                "end", bin(jle), bin(jhe))
        if jle == 0b111: # all loops end
            break

    print("transform2 pre-itersum", vec)

    # now things are in the right order for the outer butterfly.

    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, 0b0000010, 0]
    SVSHAPE0.submode2 = 0b100
    SVSHAPE0.mode = 0b01
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, 0b0000010, 0]
    SVSHAPE1.mode = 0b01
    SVSHAPE1.submode2 = 0b100
    SVSHAPE1.skip = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [0,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    i0 = iterate_dct_outer_butterfly_indices(SVSHAPE0)
    i1 = iterate_dct_outer_butterfly_indices(SVSHAPE1)
    for k, ((jl, jle), (jh, jhe)) in enumerate(zip(i0, i1)):
        print ("itersum    jr", jl, jh,
                "end", bin(jle), bin(jhe))
        vec[jl] += vec[jh]
        size //= 2
        if jle == 0b111: # all loops end
            break

    print("transform2 result", vec)

    return vec


def demo():
    # set the dimension sizes here
    n = 8
    xdim = n
    ydim = 0 # not needed
    zdim = 0 # again, not needed


    ################
    # INNER butterfly
    ################

    # set up an SVSHAPE
    class SVSHAPE:
        pass
    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, 0b000001, zdim]
    SVSHAPE0.submode2 = 0b010
    SVSHAPE0.mode = 0b01
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, 0b000001, zdim]
    SVSHAPE1.submode2 = 0b010
    SVSHAPE1.mode = 0b01
    SVSHAPE1.skip = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [0,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    schedule = []
    i0 = iterate_dct_inner_butterfly_indices(SVSHAPE0)
    i1 = iterate_dct_inner_butterfly_indices(SVSHAPE1)
    for idx, (jl, jh) in enumerate(zip(i0, i1)):
        schedule.append((jl, jh))
        if jl[1] == 0b111: # end
            break

    # ok now pretty-print the results, with some debug output
    print ("inner butterfly")
    pprint_schedule(schedule, n)
    print ("")

    ################
    # outer butterfly
    ################

    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, 0b000010, zdim]
    SVSHAPE0.mode = 0b01
    SVSHAPE0.submode2 = 0b100
    SVSHAPE0.skip = 0b10
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [1,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, 0b000010, zdim]
    SVSHAPE1.mode = 0b01
    SVSHAPE1.submode2 = 0b100
    SVSHAPE1.skip = 0b11
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [1,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    schedule = []
    i0 = iterate_dct_outer_butterfly_indices(SVSHAPE0)
    i1 = iterate_dct_outer_butterfly_indices(SVSHAPE1)
    for idx, (jl, jh) in enumerate(zip(i0, i1)):
        schedule.append((jl, jh))
        if jl[1] == 0b111: # end
            break

    # ok now pretty-print the results, with some debug output
    print ("outer butterfly")
    pprint_schedule_outer(schedule, n)

# run the demo
if __name__ == '__main__':
    demo()

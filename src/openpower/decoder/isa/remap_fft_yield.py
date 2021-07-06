# a "yield" version of the REMAP algorithm, for FFT Tukey-Cooley schedules
# original code for the FFT Tukey-Cooley schedul:
# https://www.nayuki.io/res/free-small-fft-in-multiple-languages/fft.py
"""
	# Radix-2 decimation-in-time FFT
	size = 2
	while size <= n:
		halfsize = size // 2
		tablestep = n // size
		for i in range(0, n, size):
			k = 0
			for j in range(i, i + halfsize):
                jh = j+halfsize
                jl = j
				temp1 = vec[jh] * exptable[k]
				temp2 = vec[jl]
				vec[jh] = temp2 - temp1
				vec[jl] = temp2 + temp1
				k += tablestep
		size *= 2
"""

# python "yield" can be iterated. use this to make it clear how
# the indices are generated by using natural-looking nested loops
def iterate_butterfly_indices(SVSHAPE):
    # get indices to iterate over, in the required order
    n = SVSHAPE.lims[0]
    # createing lists of indices to iterate over in each dimension
    # has to be done dynamically, because it depends on the size
    # first, the size-based loop (which can be done statically)
    x_r = []
    size = 2
    while size <= n:
        x_r.append(size)
        size *= 2
    # invert order if requested
    if SVSHAPE.invxyz[0]: x_r.reverse()

    if len(x_r) == 0:
        return

    # start an infinite (wrapping) loop
    skip = 0
    while True:
        for size in x_r:           # loop over 3rd order dimension (size)
            # y_r schedule depends on size
            halfsize = size // 2
            tablestep = n // size
            y_r = []
            for i in range(0, n, size):
                y_r.append(i)
            # invert if requested
            if SVSHAPE.invxyz[1]: y_r.reverse()
            for i in y_r:       # loop over 2nd order dimension
                k_r = []
                j_r = []
                k = 0
                for j in range(i, i+halfsize):
                    k_r.append(k)
                    j_r.append(j)
                    k += tablestep
                # invert if requested
                if SVSHAPE.invxyz[2]: k_r.reverse()
                if SVSHAPE.invxyz[2]: j_r.reverse()
                for j, k in zip(j_r, k_r):   # loop over 1st order dimension
                    # skip the first entries up to offset
                    if skip < SVSHAPE.offset:
                        skip += 1
                        continue
                    # now depending on MODE return the index
                    if SVSHAPE.skip == 0b00:
                        result = j              # for vec[j]
                    elif SVSHAPE.skip == 0b01:
                        result = j + halfsize   # for vec[j+halfsize]
                    elif SVSHAPE.skip == 0b10:
                        result = k              # for exptable[k]

                    yield result

def demo():
    # set the dimension sizes here
    xdim = 16
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

    # set up an SVSHAPE
    class SVSHAPE:
        pass
    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, ydim, zdim]
    SVSHAPE0.order = [0,1,2]  # experiment with different permutations, here
    SVSHAPE0.mode = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, ydim, zdim]
    SVSHAPE1.order = [0,1,2]  # experiment with different permutations, here
    SVSHAPE1.mode = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [0,0,0] # inversion if desired
    # k schedule
    SVSHAPE2 = SVSHAPE()
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
        schedule.append((jl, jh, k))

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

# run the demo
if __name__ == '__main__':
    demo()

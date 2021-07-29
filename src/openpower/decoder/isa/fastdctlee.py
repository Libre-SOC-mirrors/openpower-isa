#
# Fast discrete cosine transform algorithm (Python)
#
# Modifications made to create an in-place iterative DCT:
# Copyright (c) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
#
# License for modifications - SPDX: LGPLv3+
#
# Original fastdctlee.py by Nayuki:
# Copyright (c) 2020 Project Nayuki. (MIT License)
# https://www.nayuki.io/page/fast-discrete-cosine-transform-algorithms
#
# License for original fastdctlee.py by Nayuki:
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# - The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
# - The Software is provided "as is", without warranty of any kind, express or
#   implied, including but not limited to the warranties of merchantability,
#   fitness for a particular purpose and noninfringement. In no event shall the
#   authors or copyright holders be liable for any claim, damages or other
#   liability, whether in an action of contract, tort or otherwise,
#   arising from, out of or in connection with the Software or the use
#   or other dealings in the Software.
#
#
# The modifications made are firstly to create an iterative schedule,
# rather than the more normal recursive algorithm.  Secondly, the
# two butterflys are also separated out: inner butterfly does COS +/-
# whilst outer butterfly does the iterative summing.
#
# However, to avoid data copying some additional tricks are played:
# - firstly, the data is LOADed in bit-reversed order (which is normally
#   covered by the recursive algorithm due to the odd-even reconstruction)
#   but then to reference the data in the correct order an array of
#   bit-reversed indices is created, as a level of indirection.
#   the data is bit-reversed but so are the indices, making it all A-Ok.
# - secondly, normally in DCT a 2nd target (copy) array is used where
#   the top half is read in reverse order (7 6 5 4) and written out
#   to the target 4 5 6 7.  the plan was to do this in two stages:
#   write in-place in order 4 5 6 7 then swap afterwards (7-4), (6-5).
#   however by leaving the data *in-place* and having subsequent
#   loops refer to the data *where it now is*, the swap is avoided
# - thirdly, arrange for the data to be *pre-swapped* (in an inverse
#   order of how it would have got there, if that makes sense), such
#   that *when* it gets swapped, it ends up in the right order.
#   given that that will be a LD operation it's no big deal.
#
# End result is that once the first butterfly is done - bear in mind
# it's in-place - the data is in the right order so that a second
# dead-straightforward iterative sum can be done: again, in-place.
# Really surprising.

import math
from copy import deepcopy

# bits of the integer 'val'.
def reverse_bits(val, width):
    result = 0
    for _ in range(width):
        result = (result << 1) | (val & 1)
        val >>= 1
    return result


# reverse top half of a list, recursively.  the recursion can be
# applied *after* or *before* the reversal of the top half.  these
# are inverses of each other.
# this function is unused except to test the iterative version (halfrev2)
def halfrev(l, pre_rev=True):
    n = len(l)
    if n == 1:
        return l
    ll, lh = l[:n//2], l[n//2:]
    if pre_rev:
        ll, lh = halfrev(ll, pre_rev), halfrev(lh, pre_rev)
    lh.reverse()
    if not pre_rev:
        ll, lh = halfrev(ll, pre_rev), halfrev(lh, pre_rev)
    return ll + lh


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
            res.append(vec[i ^ (i>>1)])
        else:
            ri = i
            bl = i.bit_length()
            for ji in range(1, bl):
                ri ^= (i >> ji)
            res.append(vec[ri])
    return res


# DCT type II, unscaled. Algorithm by Byeong Gi Lee, 1984.
# See: http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.118.3056&rep=rep1&type=pdf#page=34
# original (recursive) algorithm by Nayuki
def transform(vector, indent=0):
    idt = "   " * indent
    n = len(vector)
    if n == 1:
        return list(vector)
    elif n == 0 or n % 2 != 0:
        raise ValueError()
    else:
        half = n // 2
        alpha = [(vector[i] + vector[-(i + 1)]) for i in range(half)]
        beta  = [(vector[i] - vector[-(i + 1)]) /
                 (math.cos((i + 0.5) * math.pi / n) * 2.0)
                    for i in range(half)]
        alpha = transform(alpha)
        beta  = transform(beta )
        result = []
        for i in range(half - 1):
            result.append(alpha[i])
            result.append(beta[i] + beta[i + 1])
        result.append(alpha[-1])
        result.append(beta [-1])
        return result


# modified recursive algorithm, based on Nayuki original, which simply
# prints out an awful lot of debug data.  used to work out the ordering
# for the iterative version by analysing the indices printed out
def transform(vector, indent=0):
    idt = "   " * indent
    n = len(vector)
    if n == 1:
        return list(vector)
    elif n == 0 or n % 2 != 0:
        raise ValueError()
    else:
        half = n // 2
        alpha = [0] * half
        beta = [0] * half
        print (idt, "xf", vector)
        print (idt, "coeff", n, "->", end=" ")
        for i in range(half):
            t1, t2 = vector[i], vector[n-i-1]
            k = (math.cos((i + 0.5) * math.pi / n) * 2.0)
            print (i, n-i-1, "i/n", (i+0.5)/n, ":", k, end= " ")
            alpha[i] = t1 + t2
            beta[i] = (t1 - t2) * (1/k)
        print ()
        print (idt, "n", n, "alpha", end=" ")
        for i in range(0, n, 2):
            print (i, i//2, alpha[i//2], end=" ")
        print()
        print (idt, "n", n, "beta", end=" ")
        for i in range(0, n, 2):
            print (i, beta[i//2], end=" ")
        print()
        alpha = transform(alpha, indent+1)
        beta  = transform(beta , indent+1)
        result = [0] * n
        for i in range(half):
            result[i*2] = alpha[i]
            result[i*2+1] = beta[i]
        print(idt, "merge", result)
        for i in range(half - 1):
            result[i*2+1] += result[i*2+3]
        print(idt, "result", result)
        return result


# totally cool *in-place* DCT algorithm
def transform2(vec):

    # Initialization
    n = len(vec)
    print ()
    print ("transform2", n)
    levels = n.bit_length() - 1

    # reference (read/write) the in-place data in *reverse-bit-order*
    ri = list(range(n))
    ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    # reference list for not needing to do data-swaps, just swap what
    # *indices* are referenced (two levels of indirection at the moment)
    # pre-reverse the data-swap list so that it *ends up* in the order 0123..
    ji = list(range(n))
    ji = halfrev2(ji, True)

    # and pretend we LDed data in half-swapped *and* bit-reversed order as well
    # TODO: merge these two
    vec = halfrev2(vec, False)
    vec = [vec[ri[i]] for i in range(n)]

    print ("ri", ri)
    print ("ji", ji)

    # create a cos table: not strictly necessary but here for illustrative
    # purposes, to demonstrate the point that it really *is* iterative.
    # this table could be cached and used multiple times rather than
    # computed every time.
    ctable = []
    size = n
    while size >= 2:
        halfsize = size // 2
        for i in range(n//size):
            for ci in range(halfsize):
                ctable.append((math.cos((ci + 0.5) * math.pi / size) * 2.0))
        size //= 2

    # start the inner butterfly
    size = n
    k = 0
    while size >= 2:
        halfsize = size // 2
        tablestep = n // size
        ir = list(range(0, n, size))
        print ("  xform", size, ir)
        for i in ir:
            # two lists of half-range indices, e.g. j 0123, jr 7654
            j = list(range(i, i + halfsize))
            jr = list(range(i+halfsize, i + size))
            jr.reverse()
            print ("  xform jr", j, jr)
            for ci, (jl, jh) in enumerate(zip(j, jr)):
                t1, t2 = vec[ri[ji[jl]]], vec[ri[ji[jh]]]
                #coeff = (math.cos((ci + 0.5) * math.pi / size) * 2.0)
                coeff = ctable[k]
                k += 1
                # normally DCT would use jl+halfsize not jh, here.
                # to be able to work in-place, the idea is to perform a
                # swap afterwards.
                vec[ri[ji[jl]]] = t1 + t2
                vec[ri[ji[jh]]] = (t1 - t2) * (1/coeff)
                print ("coeff", size, i, "ci", ci,
                        "jl", ri[ji[jl]], "jh", ri[ji[jh]],
                       "i/n", (ci+0.5)/size, coeff, vec[ri[ji[jl]]],
                                                    vec[ri[ji[jh]]])
            # instead of using jl+halfsize, perform a swap here.
            # use half of j/jr because actually jl+halfsize = reverse(j)
            hz2 = halfsize // 2 # can be zero which stops reversing 1-item lists
            for ci, (jl, jh) in enumerate(zip(j[:hz2], jr[:hz2])):
                jlh = jl+halfsize
                # swap indices, NOT the data
                tmp1, tmp2 = ji[jlh], ji[jh]
                ji[jlh], ji[jh] = tmp2, tmp1
                print ("     swap", size, i, ji[jlh], ji[jh])
        size //= 2

    print("post-swapped", ri)
    print("ji-swapped", ji)
    print("transform2 pre-itersum", vec)

    # now things are in the right order for the outer butterfly.
    n = len(vec)
    size = n // 2
    while size >= 2:
        halfsize = size // 2
        ir = list(range(0, halfsize))
        print ("itersum", halfsize, size, ir)
        for i in ir:
            jr = list(range(i+halfsize, i+n-halfsize, size))
            print ("itersum    jr", i+halfsize, i+size, jr)
            for jh in jr:
                vec[jh] += vec[jh+size]
                print ("    itersum", size, i, jh, jh+size)
        size //= 2

    print("transform2 result", vec)

    return vec


# DCT type III, unscaled. Algorithm by Byeong Gi Lee, 1984.
# See: https://www.nayuki.io/res/fast-discrete-cosine-transform-algorithms/lee-new-algo-discrete-cosine-transform.pdf
def inverse_transform(vector, root=True, indent=0):
    idt = "   " * indent
    if root:
        vector = list(vector)
        vector[0] /= 2
    n = len(vector)
    if n == 1:
        return vector, [0]
    elif n == 0 or n % 2 != 0:
        raise ValueError()
    else:
        half = n // 2
        alpha = [vector[0]]
        beta  = [vector[1]]
        for i in range(2, n, 2):
            alpha.append(vector[i])
            beta.append(vector[i - 1] + vector[i + 1])
        print (idt, "n", n, "alpha 0", end=" ")
        for i in range(2, n, 2):
            print (i, end=" ")
        print ("beta 1", end=" ")
        for i in range(2, n, 2):
            print ("%d+%d" % (i-1, i+1), end=" ")
        print()
        inverse_transform(alpha, False, indent+1)
        inverse_transform(beta , False, indent+1)
        for i in range(half):
            x, y = alpha[i], beta[i]
            coeff = (math.cos((i + 0.5) * math.pi / n) * 2)
            y /= coeff
            vector[i] = x + y
            vector[n-(i+1)] = x - y
            print (idt, " v[%d] = alpha[%d]+beta[%d]" % (i, i, i))
            print (idt, " v[%d] = alpha[%d]-beta[%d]" % (n-i-1, i, i))
        return vector


# totally cool *in-place* DCT algorithm
def inverse_transform_iter(vec):

    # Initialization
    n = len(vec)
    print ()
    print ("transform2 inv", n, vec)
    levels = n.bit_length() - 1

    # reference (read/write) the in-place data in *reverse-bit-order*
    ri = list(range(n))
    ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    # reference list for not needing to do data-swaps, just swap what
    # *indices* are referenced (two levels of indirection at the moment)
    # pre-reverse the data-swap list so that it *ends up* in the order 0123..
    ji = list(range(n))
    ji = halfrev2(ji, False)

    print ("ri", ri)
    print ("ji", ji)

    # create a cos table: not strictly necessary but here for illustrative
    # purposes, to demonstrate the point that it really *is* iterative.
    # this table could be cached and used multiple times rather than
    # computed every time.
    ctable = []
    size = n
    while size >= 2:
        halfsize = size // 2
        for i in range(n//size):
            for ci in range(halfsize):
                ctable.append((math.cos((ci + 0.5) * math.pi / size) * 2.0))
        size //= 2

    # first divide element 0 by 2
    vec[0] /= 2.0

    print("transform2-inv pre-itersum", vec)
    #vec = halfrev2(vec, True)
    #print("transform2-inv post-itersum-reorder", vec)

    # first the outer butterfly (iterative sum thing)
    n = len(vec)
    size = 2
    while size <= n:
        halfsize = size // 2
        ir = list(range(0, halfsize))
        print ("itersum", halfsize, size, ir)
        for i in ir:
            jr = list(range(i+halfsize, i+n-halfsize, size))
            jr.reverse()
            print ("itersum    jr", i+halfsize, i+size, jr)
            for jh in jr:
                #x = vec[ji[jh]]
                #y = vec[ji[jh+size]]
                #vec[ji[jh+size]] = x + y
                x = vec[jh]
                y = vec[jh+size]
                vec[jh+size] = x + y
                print ("    itersum", size, i, jh, jh+size,
                        x, y, "jh+sz", vec[ji[jh+size]])
        size *= 2

    print("transform2-inv post-itersum", vec)

    # and pretend we LDed data in half-swapped *and* bit-reversed order as well
    # TODO: merge these two
    vec = [vec[ri[i]] for i in range(n)]
    vec = halfrev2(vec, True)
    ri = list(range(n))

    print("transform2-inv post-reorder", vec)

    # start the inner butterfly (coefficients)
    size = 2
    k = 0
    while size <= n:
        halfsize = size // 2
        tablestep = n // size
        ir = list(range(0, n, size))
        print ("  xform", size, ir)
        for i in ir:
            # two lists of half-range indices, e.g. j 0123, jr 7654
            j = list(range(i, i + halfsize))
            jr = list(range(i+halfsize, i + size))
            jr.reverse()
            print ("  xform jr", j, jr)
            for ci, (jl, jh) in enumerate(zip(j, jr)):
                #t1, t2 = vec[ri[ji[jl]]], vec[ri[ji[jh]]]
                t1, t2 = vec[ji[jl]], vec[ji[jl+halfsize]]
                coeff = (math.cos((ci + 0.5) * math.pi / size) * 2.0)
                #coeff = ctable[k]
                k += 1
                # normally DCT would use jl+halfsize not jh, here.
                # to be able to work in-place, the idea is to perform a
                # swap afterwards.
                #vec[ri[ji[jl]]] = t1 + t2/coeff
                #vec[ri[ji[jh]]] = t1 - t2/coeff
                vec[ji[jl]] = t1 + t2/coeff
                vec[ji[jl+halfsize]] = t1 - t2/coeff
                print ("coeff", size, i, "ci", ci,
                        "jl", ri[ji[jl]], "jh", ri[ji[jh]],
                       "i/n", (ci+0.5)/size, coeff,
                        "t1,t2", t1, t2,
                        "+/i", vec[ji[jl]], vec[ji[jh]])
                        #"+/i", vec2[ri[ji[jl]]], vec2[ri[ji[jh]]])
            # instead of using jl+halfsize, perform a swap here.
            # use half of j/jr because actually jl+halfsize = reverse(j)
            hz2 = halfsize // 2 # can be zero which stops reversing 1-item lists
            for ci, (jl, jh) in enumerate(zip(j[:hz2], jr[:hz2])):
                jlh = jl+halfsize
                # swap indices, NOT the data
                tmp1, tmp2 = ji[jlh], ji[jh]
                ji[jlh], ji[jh] = tmp2, tmp1
                print ("     swap", size, i, ji[jlh], ji[jh])
        size *= 2

    print("post-swapped", ri)
    print("ji-swapped", ji)
    ji = list(range(n))
    ji = halfrev2(ji, True)
    print("ji-calc   ", ji)

    print("transform2-inv result", vec)

    return vec


def inverse_transform2(vector, root=True, indent=0):
    idt = "   " * indent
    n = len(vector)
    if root:
        vector = list(vector)
        vector[0] /= 2
    if n == 1:
        return vector
    elif n == 0 or n % 2 != 0:
        raise ValueError()
    else:
        print (idt, "inverse_xform2", vector)
        half = n // 2
        alpha = [vector[0]]
        beta  = [vector[1]]
        for i in range(2, n, 2):
            alpha.append(vector[i])
            beta.append(vector[i - 1] + vector[i + 1])
            print (idt, " alpha", i, vector[i])
            print (idt, " beta", i-1, i+1, vector[i-1], vector[i+1], "->",
                          beta[-1])
        inverse_transform2(alpha, False, indent+1)
        inverse_transform2(beta , False, indent+1)
        for i in range(half):
            x, y = alpha[i], beta[i]
            coeff = (math.cos((i + 0.5) * math.pi / n) * 2)
            vector[i] = x + y / coeff
            vector[n-(i+1)] = x - y / coeff
            print (idt, " v[%d] = %f+%f/%f=%f" % (i, x, y, coeff, vector[i]))
            print (idt, " v[%d] = %f-%f/%f=%f" % (n-i-1, x, y,
                                                  coeff, vector[n-i-1]))
        return vector


def inverse_transform2_explore(vector, root=True, indent=0):
    n = len(vector)
    if root:
        vector = list(vector)
    if n == 1:
        return vector
    elif n == 0 or n % 2 != 0:
        raise ValueError()
    else:
        half = n // 2
        alpha = [vector[0]]
        beta  = [vector[1]]
        for i in range(2, n, 2):
            alpha.append(vector[i])
            beta.append(("add%d" % indent, vector[i - 1], vector[i + 1]))
        inverse_transform2_explore(alpha, False, indent+1)
        inverse_transform2_explore(beta , False, indent+1)
        for i in range(half):
            x = alpha[i]
            y = ("cos%d" % indent, beta[i], i, n)
            vector[i] = ("add%d" % indent, x, y)
            vector[n-(i + 1)] = ("sub%d" % indent, x, y)
        return vector



# does the outer butterfly in a recursive fashion, used in an
# intermediary development of the in-place DCT.
def transform_itersum(vector, indent=0):
    idt = "   " * indent
    n = len(vector)
    if n == 1:
        return list(vector)
    elif n == 0 or n % 2 != 0:
        raise ValueError()
    else:
        half = n // 2
        alpha = [0] * half
        beta = [0] * half
        for i in range(half):
            t1, t2 = vector[i], vector[i+half]
            alpha[i] = t1
            beta[i] = t2
        alpha = transform_itersum(alpha, indent+1)
        beta  = transform_itersum(beta , indent+1)
        result = [0] * n
        for i in range(half):
            result[i*2] = alpha[i]
            result[i*2+1] = beta[i]
        print(idt, "iter-merge", result)
        for i in range(half - 1):
            result[i*2+1] += result[i*2+3]
        print(idt, "iter-result", result)
        return result


# prints out an "add" schedule for the outer butterfly, recursively,
# matching what transform_itersum does.
def itersum_explore(vector, indent=0):
    idt = "   " * indent
    n = len(vector)
    if n == 1:
        return list(vector)
    elif n == 0 or n % 2 != 0:
        raise ValueError()
    else:
        half = n // 2
        alpha = [0] * half
        beta = [0] * half
        for i in range(half):
            t1, t2 = vector[i], vector[i+half]
            alpha[i] = t1
            beta[i] = t2
        alpha = itersum_explore(alpha, indent+1)
        beta  = itersum_explore(beta , indent+1)
        result = [0] * n
        for i in range(half):
            result[i*2] = alpha[i]
            result[i*2+1] = beta[i]
        print(idt, "iter-merge", result)
        for i in range(half - 1):
            result[i*2+1] = ("add", result[i*2+1], result[i*2+3])
        print(idt, "iter-result", result)
        return result


# prints out the exact same outer butterfly but does so iteratively.
# by comparing the output from itersum_explore and itersum_explore2
# and by drawing out the resultant ADDs as a graph it was possible
# to deduce what the heck was going on.
def itersum_explore2(vec, indent=0):
    n = len(vec)
    size = n // 2
    while size >= 2:
        halfsize = size // 2
        ir = list(range(0, halfsize))
        print ("itersum", halfsize, size, ir)
        for i in ir:
            jr = list(range(i+halfsize, i+n-halfsize, size))
            print ("itersum    jr", i+halfsize, i+size, jr)
            for jh in jr:
                vec[jh] = ("add", vec[jh], vec[jh+size])
                print ("    itersum", size, i, jh, jh+size)
        size //= 2

    return vec

if __name__ == '__main__':
    n = 16
    vec = list(range(n))
    levels = n.bit_length() - 1
    vec = [vec[reverse_bits(i, levels)] for i in range(n)]
    ops = itersum_explore(vec)
    for i, x in enumerate(ops):
        print (i, x)

    n = 16
    vec = list(range(n))
    levels = n.bit_length() - 1
    ops = itersum_explore2(vec)
    for i, x in enumerate(ops):
        print (i, x)

    # halfrev test
    vec = list(range(16))
    print ("orig vec", vec)
    vecr = halfrev(vec, True)
    print ("reversed", vecr)
    for i, v in enumerate(vecr):
        print ("%2d %2d   %04s %04s %04s" % (i, v,
                            bin(i)[2:], bin(v ^ i)[2:], bin(v)[2:]))
    vecrr = halfrev(vecr, False)
    assert vec == vecrr
    vecrr = halfrev(vec, False)
    print ("pre-reversed", vecrr)
    for i, v in enumerate(vecrr):
        print ("%2d %2d   %04s %04s %04s" % (i, v,
                            bin(i)[2:], bin(v ^ i)[2:], bin(v)[2:]))
    il = halfrev2(vec, False)
    print ("iterative rev", il)
    il = halfrev2(vec, True)
    print ("iterative rev-true", il)

    n = 4
    vec = list(range(n))
    levels = n.bit_length() - 1
    ops = inverse_transform2_explore(vec)
    for i, x in enumerate(ops):
        print (i, x)


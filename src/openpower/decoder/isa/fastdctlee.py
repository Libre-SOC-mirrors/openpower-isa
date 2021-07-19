#
# Fast discrete cosine transform algorithms (Python)
#
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
# Modifications made to in-place iterative DCT - SPDX: LGPLv3+
# Copyright (c) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
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
#   the insight then was: to modify the *indirection* indices rather
#   than swap the actual data, and then try the same trick as was done
#   with the bit-reversed LOAD.  by a bizarre twist of good fortune
#   *that was not needed*!  simply swapping the indices was enough!
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


# modified (iterative) algorithm by lkcl, based on Nayuki original
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

    vec = deepcopy(vec)
    # Initialization
    n = len(vec)
    print ()
    print ("transform2", n)
    levels = n.bit_length() - 1

    # reference (read/write) the in-place data in *reverse-bit-order*
    ri = list(range(n))
    ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    # and pretend we LDed the data in bit-reversed order as well
    vec = [vec[reverse_bits(i, levels)] for i in range(n)]

    # create cos coefficient table
    coeffs = []
    for ci in range(n):
        coeffs.append((math.cos((ci + 0.5) * math.pi / n) * 2.0))

    # start the inner butterfly
    size = n
    while size >= 2:
        halfsize = size // 2
        tablestep = n // size
        ir = list(range(0, n, size))
        print ("  xform", size, ir)
        for i in ir:
            k = 0
            j = list(range(i, i + halfsize))
            jr = list(range(i+halfsize, i + size))
            jr.reverse()
            print ("  xform jr", j, jr)
            for ci, (jl, jh) in enumerate(zip(j, jr)):
                t1, t2 = vec[ri[jl]], vec[ri[jh]]
                # normally DCT would use jl+halfsize not jh, here.
                # to be able to work in-place, the idea is to perform a
                # high-half reverse/swap afterwards.  however actually
                # we swap the *indices*
                coeff = coeffs[k]
                vec[ri[jl]] = t1 + t2
                vec[ri[jh]] = (t1 - t2) * (1/coeff)
                print (" ", size, i, k, "ci", ci,
                        "jl", ri[jl], "jh", ri[jh],
                       "i/n", (k+0.5)/size, coeff, vec[ri[jl]], vec[ri[jh]])
                k += tablestep
            # instead of using jl+halfsize, perform a swap here.
            # use half of j/jr because actually jl+halfsize = reverse(j)
            # actually: swap the *indices*... not the actual data.
            # incredibly... bizarrely... this works *without* having
            # to do anything else.
            hz2 = halfsize // 2 # can be zero which stops reversing 1-item lists
            for ci, (jl, jh) in enumerate(zip(j[:hz2], jr[:hz2])):
                tmp = ri[jl+halfsize]
                ri[jl+halfsize] = ri[jh]
                ri[jh] = tmp
                print ("     swap", size, i, ri[jl+halfsize], ri[jh])
        size //= 2

    print("post-swapped", ri)
    print("transform2 pre-itersum", vec)

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
            x = alpha[i]
            y = beta[i] / (math.cos((i + 0.5) * math.pi / n) * 2)
            vector[i] = x + y
            vector[-(i + 1)] = x - y
            print (idt, " v[%d] = alpha[%d]+beta[%d]" % (i, i, i))
            print (idt, " v[%d] = alpha[%d]-beta[%d]" % (n-i-1, i, i))
        return vector


def inverse_transform2(vector, root=True):
    n = len(vector)
    if root:
        vector = list(vector)
    if n == 1:
        return vector
    elif n == 0 or n % 2 != 0:
        raise ValueError()
    else:
        half = n // 2
        alpha = [0]
        beta  = [1]
        for i in range(2, n, 2):
            alpha.append(i)
            beta.append(("add", i - 1, i + 1))
        inverse_transform2(alpha, False)
        inverse_transform2(beta , False)
        for i in range(half):
            x = alpha[i]
            y = ("cos", beta[i], i)
            vector[i] = ("add", x, y)
            vector[-(i + 1)] = ("sub", x, y)
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

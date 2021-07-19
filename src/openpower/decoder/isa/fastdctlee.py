#
# Fast discrete cosine transform algorithms (Python)
#
# Copyright (c) 2020 Project Nayuki. (MIT License)
# https://www.nayuki.io/page/fast-discrete-cosine-transform-algorithms
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# - The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
# - The Software is provided "as is", without warranty of any kind, express or
#   implied, including but not limited to the warranties of merchantability,
#   fitness for a particular purpose and noninfringement. In no event shall the
#   authors or copyright holders be liable for any claim, damages or other
#   liability, whether in an action of contract, tort or otherwise, arising from,
#   out of or in connection with the Software or the use or other dealings in the
#   Software.
#

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



def transform2(vec, reverse=True):

    vec = deepcopy(vec)
    # Initialization
    n = len(vec)
    print ("transform2", n)
    levels = n.bit_length() - 1

    # reference (read/write) the in-place data in *reverse-bit-order*
    if reverse:
        ri = range(n)
        ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    if reverse:
        vec = [vec[reverse_bits(i, levels)] for i in range(n)]

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
            vec2 = deepcopy(vec)
            for ci, (jl, jh) in enumerate(zip(j, jr)):
                t1, t2 = vec[ri[jl]], vec[ri[jh]]
                coeff = (math.cos((ci + 0.5) * math.pi / size) * 2.0)
                vec2[ri[jl]] = t1 + t2
                vec2[ri[jl+halfsize]] = (t1 - t2) * (1/coeff)
                print ("coeff", size, i, k, "jl", jl, "jh", jh,
                       "i/n", (k+0.5)/size, coeff, vec[ri[jl]], vec[ri[jh]])
                k += tablestep
            vec = vec2
        size //= 2

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


def failllll_transform2(block):
    N = len(block)
    cos = [0.0] * (N>>1)

    front = deepcopy(block)
    back = deepcopy(block)

    step = 1
    j = N *2
    half_N = N 
    prev_half_N = N

    while j > 1: #// Cycle of iterations Input Butterfly
        half_N = half_N >> 1
        current_PI_half_By_N = (math.pi / 2) / prev_half_N
        current_PI_By_N = 0.0
        step_Phase = current_PI_half_By_N * 2.0
        print ("n", N, "cos", end=" ")
        for i in range(half_N):
            #Precompute Cosine's coefficients
            a = current_PI_By_N + current_PI_half_By_N
            print (i, a / (math.pi), math.cos(a) * 2, end=" ")
            cos[i] = 0.5 / math.cos(a)
            current_PI_By_N += step_Phase
        print()
        k = 0
        for x in range(step):
            for i in range(half_N):
                shift = k + prev_half_N - i - 1
                back[k + i]          = front[k + i] + front[shift]
                back[k + half_N + i] = (front[k + i] - front[shift]) * cos[i]
                print ("xf coeff", N, j, i, x, "k/kh", k+i, k+half_N+i)
            k += prev_half_N
        temp = front
        front = back
        back = temp
        j = j >> 1
        step = step << 1
        prev_half_N = half_N

    half_N = 2
    prev_half_N = 2
    j = 2

    print("xform intermediate", front)

    while j < N: # Cycle of Out ButterFly
        k = 0
        print ("out", j, N, step, half_N)
        for x in range(step):
            for i in range(half_N - 1):
                back[k + (i << 1)] = front[k + i]
                back[k + (i << 1) + 1] = (front[k + half_N + i] +
                                          front[k + half_N + i + 1])
                print ("  out", j, x, i, "k", k,
                                "k+i<<1", k+(i<<1), "hh1", k+half_N+i)
            back[k + ((half_N - 1) << 1)] = front[k + half_N - 1]
            back[k + (half_N << 1) - 1] = front[k + (half_N << 1) - 1]
            k += prev_half_N

        temp = front
        front = back
        back = temp
        j = j << 1
        step = step >> 1
        half_N = prev_half_N
        prev_half_N = prev_half_N << 1

    for i in range(N):
        block[i] = front[i] #// Unload DCT coefficients
    dN = 2.0
    #block[0] = block[0] / dN #// Compute DC.

    print("transform2 result", block)
    return block


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


def itersum_explore2(vec, indent=0):
    n = len(vec)
    size = n // 2
    while size >= 2:
        halfsize = size // 2
        ir = list(range(0, halfsize))
        #ir.reverse()
        print ("itersum", halfsize, size, ir)
        for i in ir:
            jr = list(range(i+halfsize, i+n-halfsize, size))
            print ("itersum    jr", i+halfsize, i+size, jr)
            for jh in jr:
                vec[jh] = ("add", vec[jh], vec[jh+size])
                print ("    itersum", size, i, jh, jh+size)
        size //= 2

    #if reverse:
    #    vec = [vec[reverse_bits(i, levels)] for i in range(n)]

    return vec

if __name__ == '__main__':
    n = 16
    vec = list(range(n))
    levels = n.bit_length() - 1
    vec = [vec[reverse_bits(i, levels)] for i in range(n)]
    ops = itersum_explore(vec)
    #ops = [ops[reverse_bits(i, levels)] for i in range(n)]
    for i, x in enumerate(ops):
        print (i, x)

    n = 16
    vec = list(range(n))
    levels = n.bit_length() - 1
    #vec = [vec[reverse_bits(i, levels)] for i in range(n)]
    ops = itersum_explore2(vec)
    for i, x in enumerate(ops):
        print (i, x)

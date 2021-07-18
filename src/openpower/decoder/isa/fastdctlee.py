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


# DCT type II, unscaled. Algorithm by Byeong Gi Lee, 1984.
# See: http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.118.3056&rep=rep1&type=pdf#page=34
def transform(vector):
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


def transform2(vector):
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
            t1, t2 = vector[i], vector[n-i-1]
            k = (math.cos((i + 0.5) * math.pi / n) * 2.0)
            alpha[i] = t1 + t2
            beta[i] = (t1 - t2) * (1/k)
        alpha = transform2(alpha)
        beta  = transform2(beta )
        result = [0] * n
        for i in range(half):
            result[i*2] = alpha[i]
            result[i*2+1] = beta[i]
        for i in range(half - 1):
            result[i*2+1] += result[i*2+3]
        return result


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


if __name__ == '__main__':
    vector = range(8)
    ops = inverse_transform(vector)
    print (ops)

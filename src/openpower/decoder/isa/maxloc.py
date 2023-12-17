# Implementation of FORTRAN maxloc in python
# Copyright (C) Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# License: LGPLv3+
# https://bugs.libre-soc.org/show_bug.cgi?id=676#c2

from random import randint

def m2(a):
    m = 0;
    nm = 0;
    i = 0;
    n = len(a)

    while (i<n):
        while (i<n and a[i]<=m) :
            print("%d idx %d <= m %d" % ( i, a[i], m))
            i += 1
        while  (i < n and a[i] > m) :
            print("%d idx %d > m %d" % (i, a[i], m))
            m = a[i]
            nm = i
            i += 1
    return nm;

def sv_maxu(gpr, CR, vl, ra, rb, rt):
    i = 0
    while i < vl:
        CR[0] = cmpd(gpr[ra+i], gpr[rb])
        log("sv_maxss test", i, gpr[ra + i], gpr[rb], CR[0], int(CR[0]))
        gpr[rt] = gpr[ra+i] if CR[0].lt else gpr[rb]
        if not CR[0].gt:
            break
        i += 1
    return i # new VL

# this version is more akin to SVP64, using an implementation of sv.minmax
def m3(a):
    m = 0;
    nm = 0;
    i = 0;
    n = len(a)
    vl = 4

    while (i<n):
        while (i<n and a[i]<=m) :
            print("%d idx %d <= m %d" % ( i, a[i], m))
            i += 1
        while  (i < n and a[i] > m) :
            print("%d idx %d > m %d" % (i, a[i], m))
            m = a[i]
            nm = i
            i += 1
    return nm;

# /*Testbench*/

test_data = [
    ([5,2,8,1,3,7,9,4], 6),
    ([5,2,8,9,9,7,9,4], 3),
    ([0,0,0,0,0,0,0,0], 0),
    ([5,5,5,5,5,5,5,5], 0),
]

if __name__ == '__main__':
    for arr, expected in test_data:
        print("search list", arr)
        result = m2(arr)
        print("Index of the maximum value in an array is: %d" % result)
        assert (result == expected)

    # test m2 against m3
    for i in range(200):
        array_len = randint(2, 15)
        array = []
        for j in range(array_len):
            array.append(randint(0, 20))
        print("randomised search list", array)
        expected = m2(array)
        print("Index of the maximum value in an array is: %d" % expected)
        assert (m3(array) == expected)

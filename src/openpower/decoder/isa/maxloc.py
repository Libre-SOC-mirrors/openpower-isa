# Implementation of FORTRAN maxloc in python
# Copyright (C) Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# License: LGPLv3+
# https://bugs.libre-soc.org/show_bug.cgi?id=676#c2

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

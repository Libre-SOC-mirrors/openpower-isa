def m2(a):
    m = 0;
    nm = -1;
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

if __name__ == '__main__':
     arr = [5,2,8,1,3,7,9,4]
     print("search list", arr)
     result = m2(arr)
     print("Index of the maximum value in an array is: %d" % result)

     arr = [5,2,8,9,9,7,9,4]
     print("search list", arr)
     result = m2(arr)
     print("Index of the maximum value in an array is: %d" % result)

# https://stackoverflow.com/questions/14860967/
# https://stackoverflow.com/questions/7537125/

def collapse(patterns):
    """Reduce patterns into compact dash notation"""
    newPatterns = []  # reduced patterns
    matched = []      # indexes with a string that was already matched
    for x, p1 in enumerate(patterns):    # pattern1
        if x in matched: continue        # skip if this pattern already matched
        for y, p2 in enumerate(patterns[x+1:], 1):
            if x+y in matched: continue  # skip if this pattern already matched
            diffs = 0                    # number of differences found
            for idx, bit in enumerate(zip(p1, p2)):
                if bit[0] != bit[1]:     # count of bits that are different
                    diffs += 1
                    dbit = idx
                if diffs > 1: break
            # if exactly 1 bit different between the two,
            # they can be compressed together
            if diffs == 1:
                newPatterns.append('-'.join([p1[:dbit], p1[dbit+1:]]))
                matched+=[x,x+y]
                break
        # if the pattern wasn't matched, just append it as is.
        if x not in matched: newPatterns.append(p1)

    # if reductions occurred on this run, then call again
    # to check if more are possible.
    if matched:
        newPatterns = collapse(newPatterns)

    return newPatterns

if __name__ == '__main__':
    
    isel = [
    "0000001111",
    "0000101111",
    "0001001111",
    "0001101111",
    "0010001111",
    "0010101111",
    "0011001111",
    "0011101111",
    "0100001111",
    "0100101111",
    "0101001111",
    "0101101111",
    "0110001111",
    "0110101111",
    "0111001111",
    "0111101111",
    "1000001111",
    "1000101111",
    "1001001111",
    "1001101111",
    "1010001111",
    "1010101111",
    "1011001111",
    "1011101111",
    "1100001111",
    "1100101111",
    "1101001111",
    "1101101111",
    "1110001111",
    "1110101111",
    "1111001111",
    "1111101111",
    ]
    isel1 = collapse(isel)
    print ("isel", isel1)

    svshape = [
    "0000-011001",
    "0001-011001",
    "0010-011001",
    "0011-011001",
    "0100-011001",
    "0101-011001",
    "0110-011001",
    "0111-011001",
    "1010-011001",
    "1011-011001",
    "1100-011001",
    "1101-011001",
    "1110-011001",
    "1111-011001",
    ]

    svshape1 = collapse(svshape)
    print ("svshape", svshape1)

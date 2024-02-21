"""
Copyright (C) 2023 2024 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
License: LGPLv3+
Funding: NLnet NGI-ASSURE Project funded under EU grant agreement No 957073.
"""

"""
start here... https://bugs.libre-soc.org/show_bug.cgi?id=773#c1

t[0]  =  r0 * s0
t[1]  =  r0 * s1 + r1 * s0;
t[2]  =  r0 * s2 + r1 * s1 + r2 * s0;
t[3]  =  r0 * s3 + r1 * s2 + r2 * s1 + r3 * s0;
t[4]  =  r0 * s4 + r1 * s3 + r2 * s2 + r3 * s1 + r4 * s0;

	r1 *= 19;
	r2 *= 19;
	r3 *= 19;
	r4 *= 19;

t[0] += r4 * s1 + r3 * s2 + r2 * s3 + r1 * s4;
t[1] += r4 * s2 + r3 * s3 + r2 * s4;
t[2] += r4 * s3 + r3 * s4;
t[3] += r4 * s4;

                     r0 = lo128(t[0]) & reduce_mask_51; shr128(c, t[0], 51);
add128_64(t[1], c)   r1 = lo128(t[1]) & reduce_mask_51; shr128(c, t[1], 51);
add128_64(t[2], c)   r2 = lo128(t[2]) & reduce_mask_51; shr128(c, t[2], 51);
add128_64(t[3], c)   r3 = lo128(t[3]) & reduce_mask_51; shr128(c, t[3], 51);
add128_64(t[4], c)   r4 = lo128(t[4]) & reduce_mask_51; shr128(c, t[4], 51);
r0 +=   c * 19; c = r0 >> 51; r0 = r0 & reduce_mask_51;
r1 +=   c;

"""

import random

def curve25519_mul(r, s):

    t = [0] * 5

    for i in range(5):
        print("t%d += " % i, end='')
        for j in range(i+1):
            sidx = i-j
            print("r%d*s%d + " % (i, sidx), end='')
            t[i] += r[i] * s[sidx]
        print()

    for i in range(1,5):
        r[i] *= 19

    print()
    for i in range(4,0,-1):
        tidx = 4-i
        print("t%d += " % tidx, end='')
        for j in range(i):
            jidx, sidx = 4-j, 5-(i-j)
            print("r%d*s%d + " % (jidx, sidx), end='')
            t[tidx] += r[jidx] * s[sidx]
        print()

    # this is the one where i *think* it possible to do some sort
    # of single-operation similar to dsld.

    c = 0
    for i in range(5):
        add128_64(t[i], c);
        r[i] = lo128(t[i]) & reduce_mask_51;
        shr128(c, t[i], 51);

    r[0] +=   c * 19; c = r[0] >> 51; r[0] = r[0] & reduce_mask_51;
    r[1] +=   c;

if __name__ == '__main__':
    random.seed(2) # set the same seed (consistent test)
    r, s = [], []
    for j in range(5):
        r.append(random.randint(0, 2^50))
        s.append(random.randint(0, 2^50))
    print ("r", r)
    print ("s", s)
    t = curve25519_mul(r, s)
    print ("t", t)

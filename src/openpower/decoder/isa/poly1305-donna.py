# Copyright (c) 2023, Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Licensed under the LGPLv3+
# Funded by NLnet NGI-ASSURE under EU grant agreement No 957073.
# * https://nlnet.nl/project/LibreSOC-GigabitRouter/
# * https://bugs.libre-soc.org/show_bug.cgi?id=1157
# * Based on https://github.com/floodyberry/poly1305-donna (Public Domain)
"""Implementation of Poly1305 authenticator for RFC 7539
Design principles are well-documented at:
https://loup-vaillant.fr/tutorials/poly1305-design
"""

def divceil(a, b): return -(a // -b)

poly1305_block_size = 16

mask128 = (1<<128)-1
mask64 = (1<<64)-1
def _MUL(x, y): out = (x&mask64) * (y&mask64); print("mul %x*%x=%x" % (x, y, out)); return out
def _ADD(out, i): return (out + i)
def _ADDLO(out, i): return (out + (i & mask64))
def _SHR(i, shift): out = (i >> shift) & mask64; print("shr %x>>%d=%x mask %x" % (i,shift,out,mask64)); return out
def _LO(i): return i & mask64


# this function is extracted from bigint_cases.py (should be in a library)
# it is a python implementation of dsrd, see pseudocode in
# https://libre-soc.org/openpower/isa/svfixedarith/
def _DSRD(lo, hi, sh):
    sh = sh % 64
    v = lo << 64
    v >>= sh
    mask = ~((2 ** 64 - 1) >> sh)
    v |= (hi & mask) << 64
    hi = (v >> 64) % (2 ** 64)
    lo = v % (2 ** 64)
    return lo, hi

# interception function which allows analysis of carry-roll-over
intercepts = {}

def log(p1305, fn, result, args):
    """intercept of mathematical primitives is recorded, so that
    analysis is possible to find any carry-roll-over occurrences.
    these we *assume* are when one of the add arguments is between
    0 and say... 7?
    """
    name = fn.__name__[1:]
    if name in ['ADD', 'ADDLO']:
        # rright. the 2nd parameter, if between the values 0 and 7,
        # is assumed to be some sort of carry. everything else is ignored
        arg1, arg2 = args
        if arg2 > 7:
            return
    else: # only interested in adds for now
        return
    # begin hashing and adding this operation into the intercepts log
    phash = hash(p1305)
    info = (name, result, args)
    key = hash(info)
    logreport = "%5s %x <= " % (name, result)
    logreport = logreport + " ".join(list(map(lambda x: "%x" % x, args)))
    intercepts[key] = logreport

def intercept(p1305, args, fn):
    result = fn(*args)
    log(p1305, fn, result, args)
    return result


class Ctx:
    """A ContextManager for noting the inputs and outputs for interception.
    The idea is to create unit tests with these same inputs and record
    the expected outputs
    """

    def __init__(self, log, variables, inputs, outputs):
        self.log = log
        self.variables = variables
        self.inputs = inputs
        self.outputs = outputs

    def print_vars(self, varnames):
        for v in varnames:
            print("    %s %s" % (v, repr(self.variables[v])))

    def __enter__(self):
        print("enter")
        self.print_vars(self.inputs)

    def __exit__(self, *args):
        print("exit", args, self.outputs)
        self.print_vars(self.outputs)


class Poly1305Donna(object):

    """Poly1305 authenticator"""

    P = 0x3fffffffffffffffffffffffffffffffb # 2^130-5

    # suite of primitives (128-bit and 64-bit) which can be intercepted
    # here in order to analyse carry-roll-over
    def MUL(self, *args): return intercept(self, args, _MUL) # x,y
    def ADD(self, *args): return intercept(self, args, _ADD) # out,i
    def ADDLO(self, *args): return intercept(self, args, _ADDLO) # out,i
    def SHR(self, *args): return intercept(self, args, _SHR) # i,shift
    def LO(self, *args): return intercept(self, args, _LO) # i
    def DSRD(self, *args): return intercept(self, args, _DSRD) # lo,hi,sh

    @staticmethod
    def le_bytes_to_num(data):
        """Convert a number from little endian byte format"""
        ret = 0
        for i in range(len(data) - 1, -1, -1):
            ret <<= 8
            ret += data[i]
        return ret

    @staticmethod
    def num_to_16_le_bytes(num):
        """Convert number to 16 bytes in little endian format"""
        ret = [0]*16
        for i, _ in enumerate(ret):
            ret[i] = num & 0xff
            num >>= 8
        return bytearray(ret)

    def __init__(self, key):
        """Set the authenticator key"""
        if len(key) != 32:
            raise ValueError("Key must be 256 bit long")

        self.buffer = [0]*16
        self.acc = 0
        self.r = self.le_bytes_to_num(key[0:16])
        self.r &= 0x0ffffffc0ffffffc0ffffffc0fffffff
        self.s = self.le_bytes_to_num(key[16:32])

        # r &= 0xffffffc0ffffffc0ffffffc0fffffff */
        t = self.t = [0]*2
        t[0] = self.le_bytes_to_num(key[0:8])  # t0 = U8TO64(&key[0]);
        t[1] = self.le_bytes_to_num(key[8:16]) # t1 = U8TO64(&key[8]);

        print ("init t %x %x" % (t[0], t[1]))

        r = self.r = [0]*3
        with Ctx("init r<-t", locals(), ["r"], ["t"]):
            r[0] = ( t[0]                      ) & 0xffc0fffffff
            r[1] = ((t[0] >> 44) | (t[1] << 20)) & 0xfffffc0ffff
            r[2] = ((t[1] >> 24)               ) & 0x00ffffffc0f

        # h = 0 */
        h = self.h = [0]*3

        # save pad for later */
        pad = self.pad = [0]*2
        pad[0] = self.le_bytes_to_num(key[16:24])
        pad[1] = self.le_bytes_to_num(key[24:32])

        self.leftover = 0
        self.final = 0

    def poly1305_blocks(self, m):

        # get local-names for math-primitives to look like poly1305-donna-64.h
        MUL, ADD, ADDLO, SHR, LO = \
            self.MUL, self.ADD, self.ADDLO, self.SHR, self.LO

        hibit = 0 if self.final else 1 << 40 # 1 << 128
        #unsigned long long r0,r1,r2;
        #unsigned long long s1,s2;
        #unsigned long long h0,h1,h2;
        #unsigned long long c;
        #uint128_t d0,d1,d2,d;

        r0 = self.r[0];
        r1 = self.r[1];
        r2 = self.r[2];

        h0 = self.h[0];
        h1 = self.h[1];
        h2 = self.h[2];

        s1 = r1 * (5 << 2);
        s2 = r2 * (5 << 2);

        print("blocks r %x %x %x" % (r0, r1, r2))
        print("blocks h %x %x %x" % (h0, h1, h2))
        print("blocks s %x %x" % (s1, s2))

        while len(m) >= poly1305_block_size:
            #unsigned long long t0,t1;

            #/* h += m[i] */
            t0 = self.le_bytes_to_num(m[0:8])
            t1 = self.le_bytes_to_num(m[8:16])

            print("    loop t %x %x" % (t0, t1))

            h0 += (( t0                    ) & 0xfffffffffff);
            h1 += (((t0 >> 44) | (t1 << 20)) & 0xfffffffffff);
            h2 += (((t1 >> 24)             ) & 0x3ffffffffff) | hibit;

            print("    loop h+t %x %x %x" % (h0, h1, h2))

            #/* h *= r */
            d0=MUL(h0,r0); d=MUL(h1,s2);
            print("      h*=r d0 d %x %x" % (d0, d))
            d0+=d; d=MUL(h2,s1); d0+=d;
            d1=MUL(h0,r1);d=MUL(h1,r0);d1=ADD(d1,d);d=MUL(h2,s2);d1=ADD(d1,d);
            d2=MUL(h0,r2);d=MUL(h1,r1);d2=ADD(d2,d);d=MUL(h2,r0);d2=ADD(d2,d);
            print("      after h*=r d0 d1 d2 %x %x %x %x" % (d0, d1, d2, d))

            #/* (partial) h %= p */
            c = 0
            d0 = ADDLO(d0,c); c = SHR(d0, 44); h0 = LO(d0) & 0xfffffffffff;
            d1 = ADDLO(d1,c); c = SHR(d1, 44); h1 = LO(d1) & 0xfffffffffff;
            d2 = ADDLO(d2,c); c = SHR(d2, 42); h2 = LO(d2) & 0x3ffffffffff;
            h0 += MUL(c, 5);  c = (h0 >> 44) ; h0 =    h0  & 0xfffffffffff;
            h1 += MUL(c, 1);

            m = m[poly1305_block_size:]

        self.h[0] = h0;
        self.h[1] = h1;
        self.h[2] = h2;

    def poly1305_finish(self):

        # get local-names for math-primitives to look like poly1305-donna-64.h
        MUL, ADD, ADDLO, SHR, LO = \
            self.MUL, self.ADD, self.ADDLO, self.SHR, self.LO

        #unsigned long long h0,h1,h2,c;
        #unsigned long long g0,g1,g2;
        #unsigned long long t0,t1;

        #/* process the remaining block */
        if self.leftover:
            i = self.leftover;
            self.buffer[i] = 1;
            for i in range(i+1, poly1305_block_size):
                self.buffer[i] = 0;
            self.final = 1;
            self.poly1305_blocks(self.buffer)

        f3, ff = 0x3ffffffffff, 0xfffffffffff

        #/* fully carry h */
        h0 = self.h[0];
        h1 = self.h[1];
        h2 = self.h[2];

        print("finish %x %x %x" % (h0, h1, h2))

        # commented-out from the original (left in for comparison),
        # see https://bugs.libre-soc.org/show_bug.cgi?id=1157#c3
        # as to what is going on here

        #c = 0
        #h1 += c;     c = (h1 >> 44); h1 &= ff;
        #h2 += c;     c = (h2 >> 42); h2 &= f3;
        #h0 += c * 5; c = (h0 >> 44); h0 &= ff;
        #h1 += c;     c = (h1 >> 44); h1 &= ff;
        #h2 += c;     c = (h2 >> 42); h2 &= f3;
        #h0 += c * 5; c = (h0 >> 44); h0 &= ff;
        #h1 += c;

        # okaaay, first "preparation" for conversion to SVP64 REMAP/Indexed:
        # extract the constants/indices from the original above and look for the
        # common pattern, which is:
        # h? += c * ?; c = (h? >> ??); h? &= ??;

        # these appear to be repeated twice
        idxconsts = [ # hN c* shf
                       [1, 1, 44],
                       [2, 1, 42],
                       [0, 5, 44]
                    ]
        c = 0 # start with carry=0
        for hidx, cmul, shf in idxconsts*2: # repeat the pattern twice
            self.h[hidx] += MUL(c, cmul)    # don't worry about *1
            c = self.h[hidx] >> shf         # these two could use dsrd
            self.h[hidx] &= (1<<shf) - 1    # (one instruction)
        self.h[1] += c; # can't have everything...

        h0, h1, h2 = self.h

        print("    h0-2 %x %x %x" % (h0, h1, h2))

        #/* compute h + -p */
        c = 5
        g0 = ADD(h0, c); c = (g0 >> 44); g0 &= ff;
        g1 = ADD(h1, c); c = (g1 >> 44); g1 &= ff;
        g2 = (ADD(h2, c) - (1 << 42)) & mask64

        print("    g0-2 %x %x %x" % (g0, g1, g2))

        #/* select h if h < p, or h + -p if h >= p */
        c = (g2 >> ((8 * 8) - 1)) - 1;
        print("    c %x" % c)
        g0 &= c;
        g1 &= c;
        g2 &= c;
        c = ~c;
        h0 = (h0 & c) | g0;
        h1 = (h1 & c) | g1;
        h2 = (h2 & c) | g2;

        #/* h = (h + pad) */
        t0 = self.pad[0];
        t1 = self.pad[1];

        h0 += ADD(( t0                    ) & ff, 0); c = (h0 >> 44); h0 &= ff;
        h1 += ADD(((t0 >> 44) | (t1 << 20)) & ff, c); c = (h1 >> 44); h1 &= ff;
        h2 += ADD(((t1 >> 24)             ) & f3, c);                 h2 &= f3;

        #/* mac = h % (2^128) */
        h0 = ((h0      ) | (h1 << 44));
        h1 = ((h1 >> 20) | (h2 << 24));

        mac = [0]*16
        mac[0:8] = self.num_to_16_le_bytes(h0)[0:8]
        mac[8:16] = self.num_to_16_le_bytes(h1)[0:8]

        # /* zero out the state */
        self.h[0] = 0;
        self.h[1] = 0;
        self.h[2] = 0;
        self.r[0] = 0;
        self.r[1] = 0;
        self.r[2] = 0;
        self.pad[0] = 0;
        self.pad[1] = 0;

        return bytearray(mac)

    def poly1305_update(self, m):

        #/* handle leftover */
        if (self.leftover):
            want = (poly1305_block_size - self.leftover);
            if (want > len(m)):
                want = len(m);
            for i in range(want):
                self.buffer[self.leftover + i] = m[i];
            m = m[want:]
            self.leftover += want;
            if (self.leftover < poly1305_block_size):
                return;
            self.poly1305_blocks(self.buffer);
            self.leftover = 0;

        # /* process full blocks */
        if (len(m) >= poly1305_block_size):
            want = (len(m) & ~(poly1305_block_size - 1));
            self.poly1305_blocks(m[:want]);
            m = m[want:]

        # /* store leftover */
        for i in range(len(m)):
            self.buffer[self.leftover + i] = m[i];
        self.leftover += len(m);

    def create_tag(self, data):
        """Calculate authentication tag for data"""
        self.poly1305_update(data)
        return self.poly1305_finish()


# quick usage demo, make identical to poly1305-donna/example-poly1305.c
if __name__ == '__main__':
    key = list(range(221, 253))
    mac = Poly1305Donna(key).create_tag(bytearray(range(121,121+73)))
    print("result hash:", end=" ")
    for byte in mac:
        print(hex(byte)[2:], sep='', end='')
    print()

    # print out the intercepts
    for intercept in intercepts.values():
        print (intercept)

    expected = [0xdd,0xb9,0xda,0x7d,0xdd,0x5e,0x52,0x79,
                0x27,0x30,0xed,0x5c,0xda,0x5f,0x90,0xa4]
    assert mac == bytearray(expected)


# Copyright (c) 2023, Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Licensed under the LGPLv3+
# Funded by NLnet NGI-ASSURE under EU grant agreement No 957073.
# * https://nlnet.nl/project/LibreSOC-GigabitRouter/
# * https://bugs.libre-soc.org/show_bug.cgi?id=1157
# * Based on https://github.com/floodyberry/poly1305-donna (Public Domain)
"""Implementation of Poly1305 authenticator for RFC 7539"""

def divceil(a, b): return -(a // -b)

poly1305_block_size = 16

mask128 = (1<<128)-1
mask64 = (1<<64)-1
def MUL(x, y): out = (x&mask64) * (y&mask64); print("mul %x*%x=%x" % (x, y, out)); return out
def ADDLO(out, i): return (out + (i & mask64))
def SHR(i, shift): out = (i >> shift) & mask64; print("shr %x>>%d=%x mask %x" % (i,shift,out,mask64)); return out 
def LO(i): return i & mask64

class Poly1305Donna(object):

    """Poly1305 authenticator"""

    P = 0x3fffffffffffffffffffffffffffffffb # 2^130-5

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
            d1=MUL(h0,r1); d=MUL(h1,r0); d1+=d; d=MUL(h2,s2); d1+=d;
            d2=MUL(h0,r2); d=MUL(h1,r1); d2+=d; d=MUL(h2,r0); d2+=d;
            print("      after h*=r d0 d1 d2 %x %x %x %x" % (d0, d1, d2, d))

            #/* (partial) h %= p */
            c = 0
            d0 = ADDLO(d0,c); c = SHR(d0, 44); h0 = LO(d0) & 0xfffffffffff;
            d1 = ADDLO(d1,c); c = SHR(d1, 44); h1 = LO(d1) & 0xfffffffffff;
            d2 = ADDLO(d2,c); c = SHR(d2, 42); h2 = LO(d2) & 0x3ffffffffff;
            h0 += c * 5     ; c = (h0 >> 44) ; h0 =    h0  & 0xfffffffffff;
            h1 += c;

            m = m[poly1305_block_size:]

        self.h[0] = h0;
        self.h[1] = h1;
        self.h[2] = h2;

    def poly1305_finish(self):
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

        c = 0
        h1 += c;     c = (h1 >> 44); h1 &= ff;
        h2 += c;     c = (h2 >> 42); h2 &= f3;
        h0 += c * 5; c = (h0 >> 44); h0 &= ff;
        h1 += c;     c = (h1 >> 44); h1 &= ff;
        h2 += c;     c = (h2 >> 42); h2 &= f3;
        h0 += c * 5; c = (h0 >> 44); h0 &= ff;
        h1 += c;

        print("    h0-2 %x %x %x" % (h0, h1, h2))

        #/* compute h + -p */
        g0 = h0 + 5; c = (g0 >> 44); g0 &= ff;
        g1 = h1 + c; c = (g1 >> 44); g1 &= ff;
        g2 = (h2 + c - (1 << 42)) & mask64

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

        h0 += (( t0                    ) & ff)    ; c = (h0 >> 44); h0 &= ff;
        h1 += (((t0 >> 44) | (t1 << 20)) & ff) + c; c = (h1 >> 44); h1 &= ff;
        h2 += (((t1 >> 24)             ) & f3) + c;                 h2 &= f3;

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
    for byte in mac:
        print(hex(byte)[2:], sep='', end='')
    print()
    expected = [0xdd,0xb9,0xda,0x7d,0xdd,0x5e,0x52,0x79,
                0x27,0x30,0xed,0x5c,0xda,0x5f,0x90,0xa4]
    assert mac == bytearray(expected)

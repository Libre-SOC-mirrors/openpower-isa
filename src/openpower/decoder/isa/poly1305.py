# Copyright (c) 2015, Hubert Kario
# License: LGPLv2.1
"""Implementation of Poly1305 authenticator for RFC 7539"""

def divceil(a, b): return -(a // -b)

class Poly1305(object):

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
        self.acc = 0
        self.r = self.le_bytes_to_num(key[0:16])
        self.r &= 0x0ffffffc0ffffffc0ffffffc0fffffff
        self.s = self.le_bytes_to_num(key[16:32])

    def create_tag(self, data):
        """Calculate authentication tag for data"""
        for i in range(0, divceil(len(data), 16)):
            n = self.le_bytes_to_num(data[i*16:(i+1)*16] + b'\x01')
            self.acc += n
            self.acc = (self.r * self.acc) % self.P
        self.acc += self.s
        return self.num_to_16_le_bytes(self.acc)


# quick usage demo, make identical to poly1305-donna/example-poly1305.c
if __name__ == '__main__':
    key = list(range(221, 253))
    mac = Poly1305(key).create_tag(bytearray(range(121,121+73)))
    for byte in mac:
        print(hex(byte)[2:], sep='', end='')
    print()
    expected = [0xdd,0xb9,0xda,0x7d,0xdd,0x5e,0x52,0x79,
                0x27,0x30,0xed,0x5c,0xda,0x5f,0x90,0xa4]
    assert mac == bytearray(expected)

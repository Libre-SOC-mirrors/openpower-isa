# SPDX-License-Identifier: LGPLv3+
# Funded by NLnet https://nlnet.nl/

""" implementation of binary floating-point working format as used in:
PowerISA v3.1B section 7.6.2.2
e.g. bfp_CONVERT_FROM_BFP32() on page 589(615)
"""

from openpower.decoder.selectable_int import SelectableInt
import operator
import math
from fractions import Fraction

# in this file, everything uses properties instead of plain attributes because
# we need to convert most SelectableInts we get to Python int


class BFPStateClass:
    def __init__(self, value=None):
        self.__snan = 0
        self.__qnan = 0
        self.__infinity = 0
        self.__zero = 0
        self.__denormal = 0
        self.__normal = 0
        if value is not None:
            self.eq(value)

    def eq(self, rhs):
        self.SNaN = rhs.SNaN
        self.QNaN = rhs.QNaN
        self.Infinity = rhs.Infinity
        self.Zero = rhs.Zero
        self.Denormal = rhs.Denormal
        self.Normal = rhs.Normal

    @property
    def SNaN(self):
        return self.__snan

    @SNaN.setter
    def SNaN(self, value):
        self.__snan = int(value)

    @property
    def QNaN(self):
        return self.__qnan

    @QNaN.setter
    def QNaN(self, value):
        self.__qnan = int(value)

    @property
    def Infinity(self):
        return self.__infinity

    @Infinity.setter
    def Infinity(self, value):
        self.__infinity = int(value)

    @property
    def Zero(self):
        return self.__zero

    @Zero.setter
    def Zero(self, value):
        self.__zero = int(value)

    @property
    def Denormal(self):
        return self.__denormal

    @Denormal.setter
    def Denormal(self, value):
        self.__denormal = int(value)

    @property
    def Normal(self):
        return self.__normal

    @Normal.setter
    def Normal(self, value):
        self.__normal = int(value)

    def __eq__(self, other):
        if isinstance(other, BFPStateClass):
            return (self.SNaN == other.SNaN and
                    self.QNaN == other.QNaN and
                    self.Infinity == other.Infinity and
                    self.Zero == other.Zero and
                    self.Denormal == other.Denormal and
                    self.Normal == other.Normal)
        return NotImplemented

    def _bfp_state_fields(self):
        return (f"class_.SNaN: {self.SNaN}",
                f"class_.QNaN: {self.QNaN}",
                f"class_.Infinity: {self.Infinity}",
                f"class_.Zero: {self.Zero}",
                f"class_.Denormal: {self.Denormal}",
                f"class_.Normal: {self.Normal}")

    def __repr__(self):
        fields = self._bfp_state_fields()
        return f"<BFPStateClass {fields}>"


class SelectableMSB0Fraction:
    """a MSB0 infinite bit string that is really a real number between 0 and 1,
    but we approximate it using a Fraction.

    this is not just SelectableInt because we need more than 256 bits and
    because this isn't an integer.
    """

    def __init__(self, value=None):
        self.__value = Fraction()
        self.eq(value)

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, v):
        self.__value = Fraction(v)

    @staticmethod
    def __get_slice_dimensions(index):
        if isinstance(index, slice):
            if index.stop is None or index.step is not None:
                raise ValueError("unsupported slice kind")
            # use int() to convert from
            start = int(0 if index.start is None else index.start)
            stop = int(index.stop)
            length = stop - start + 1
        else:
            start = int(index)
            length = 1
        return start, length

    def __slice_as_int(self, start, length):
        if start < 0 or length < 0:
            raise ValueError("slice out of range")
        end = start + length
        # shift so bits we want are the lsb bits of the integer part
        v = math.floor(self.value * (1 << end))
        return v & ~(~0 << length)  # mask off unwanted bits

    def __set_slice(self, start, length, value):
        if start < 0 or length < 0:
            raise ValueError("slice out of range")
        end = start + length
        shift_factor = 1 << end
        # shift so bits we want to replace are the lsb bits of the integer part
        v = self.value * shift_factor
        mask = ~(~0 << length)
        # convert any SelectableInts to int and mask
        value = int(value) & mask
        # compute how much we need to add
        offset = value - (math.floor(v) & mask)
        # shift offset back into position
        offset /= shift_factor
        self.value += offset

    def __getitem__(self, index):
        start, length = self.__get_slice_dimensions(index)
        return SelectableInt(self.__slice_as_int(start, length), length)

    def __setitem__(self, index, value):
        start, length = self.__get_slice_dimensions(index)
        self.__set_slice(start, length, value)

    def __str__(self, *,
                max_int_digits=4,  # don't need much since this is generally
                                   # supposed to be in [0, 1]
                max_fraction_digits=17,  # u64 plus 1
                fraction_sep_period=4,  # how many fraction digits between `_`s
                ):
        """ convert to a string of the form: `0x3a.bc` or
        `0x...face.face_face_face_face... (0xa8ef0000 / 0x5555)`"""
        if max_int_digits < 0 or max_fraction_digits < 0:
            raise ValueError("invalid digit limit")
        approx = False
        int_part = math.floor(self.value)
        int_part_limit = 0x10 ** max_int_digits
        if 0 <= int_part < int_part_limit:
            int_str = hex(int_part)
        else:
            approx = True
            int_part %= int_part_limit
            int_str = f"0x...{int_part:0{max_int_digits}x}"

        # is the denominator a power of 2?
        if (self.value.denominator & (self.value.denominator - 1)) == 0:
            fraction_bits = self.value.denominator.bit_length() - 1
            fraction_digits = -(-fraction_bits) // 4  # ceil division by 4
        else:
            # something bigger than max_fraction_digits
            fraction_digits = max_fraction_digits + 1
        if fraction_digits > max_fraction_digits:
            suffix = "..."
            approx = True
            fraction_digits = max_fraction_digits
        else:
            suffix = ""
        factor = 0x10 ** fraction_digits
        fraction_part = math.floor(self.value * factor)
        fraction_str = f"{fraction_part:0{fraction_digits}x}"
        fraction_parts = []
        if fraction_sep_period is not None and fraction_sep_period > 0:
            for i in range(0, len(fraction_str), fraction_sep_period):
                fraction_parts.append(fraction_str[i:i + fraction_sep_period])
            fraction_str = "_".join(fraction_parts)
        fraction_str = "." + fraction_str + suffix
        retval = int_str
        if self.value.denominator != 1:
            retval += fraction_str
        if approx:
            n = self.value.numerator
            d = self.value.denominator
            retval += f" ({n:#x} / {d:#x})"
        return retval

    def __repr__(self):
        return "SelectableMSB0Fraction(" + str(self) + ")"

    def eq(self, value):
        if isinstance(value, (int, Fraction)):
            self.value = Fraction(value)
        elif isinstance(value, SelectableMSB0Fraction):
            self.value = value.value
        else:
            raise ValueError("unsupported assignment type")

    def __bool__(self):
        return self.value != 0

    def __neg__(self):
        return SelectableMSB0Fraction(-self.value)

    def __pos__(self):
        return SelectableMSB0Fraction(self)

    @staticmethod
    def __arith_op(lhs, rhs, op):
        lhs = SelectableMSB0Fraction(lhs)
        rhs = SelectableMSB0Fraction(rhs)
        return SelectableMSB0Fraction(op(lhs.value, rhs.value))

    def __add__(self, other):
        return self.__arith_op(self, other, operator.add)

    __radd__ = __add__

    def __mul__(self, other):
        return self.__arith_op(self, other, operator.mul)

    __rmul__ = __mul__

    def __sub__(self, other):
        return self.__arith_op(self, other, operator.sub)

    def __rsub__(self, other):
        return self.__arith_op(other, self, operator.sub)

    def __truediv__(self, other):
        return self.__arith_op(self, other, operator.truediv)

    def __rtruediv__(self, other):
        return self.__arith_op(other, self, operator.truediv)

    def __lshift__(self, amount):
        if not isinstance(amount, int):
            raise TypeError("can't shift by non-int")
        if amount < 0:
            return SelectableMSB0Fraction(self.value / (1 << -amount))
        return SelectableMSB0Fraction(self.value * (1 << amount))

    def __rlshift__(self, other):
        raise TypeError("can't shift by non-int")

    def __rshift__(self, amount):
        if not isinstance(amount, int):
            raise TypeError("can't shift by non-int")
        return self << -amount

    def __rrshift__(self, other):
        raise TypeError("can't shift by non-int")

    def __cmp_op(self, other, op):
        if isinstance(other, (int, Fraction)):
            pass
        elif isinstance(other, SelectableMSB0Fraction):
            other = other.value
        else:
            return NotImplemented
        return op(self.value, other)

    def __eq__(self, other):
        return self.__cmp_op(self, other, operator.eq)

    def __ne__(self, other):
        return self.__cmp_op(self, other, operator.ne)

    def __lt__(self, other):
        return self.__cmp_op(self, other, operator.lt)

    def __le__(self, other):
        return self.__cmp_op(self, other, operator.le)

    def __gt__(self, other):
        return self.__cmp_op(self, other, operator.gt)

    def __ge__(self, other):
        return self.__cmp_op(self, other, operator.ge)


class BFPState:
    """ implementation of binary floating-point working format as used in:
    PowerISA v3.1B section 7.6.2.2
    e.g. bfp_CONVERT_FROM_BFP32() on page 589(615)
    """

    def __init__(self, value=None):
        self.__sign = 0
        self.__exponent = 0
        self.__significand = SelectableMSB0Fraction()
        self.__class = BFPStateClass()
        if value is not None:
            self.eq(value)

    def eq(self, rhs):
        self.sign = rhs.sign
        self.exponent = rhs.exponent
        self.significand = rhs.significand
        self.class_ = rhs.class_

    @property
    def sign(self):
        return self.__sign

    @sign.setter
    def sign(self, value):
        self.__sign = int(value)

    @property
    def exponent(self):
        return self.__exponent

    @exponent.setter
    def exponent(self, value):
        self.__exponent = int(value)

    @property
    def significand(self):
        return self.__significand

    @significand.setter
    def significand(self, value):
        self.__significand.eq(value)

    @property
    def class_(self):
        return self.__class

    @class_.setter
    def class_(self, value):
        self.__class.eq(value)

    def __eq__(self, other):
        if isinstance(other, BFPStateClass):
            return self._bfp_state_fields() == other._bfp_state_fields()
        return NotImplemented

    def _bfp_state_fields(self):
        class_fields = self.class_._bfp_state_fields()
        return (f"sign: {self.sign}",
                f"exponent: {self.exponent}",
                f"significand: {self.significand}",
                *self.class_._bfp_state_fields())

    def __repr__(self):
        fields = self._bfp_state_fields()
        return f"<BFPState {fields}>"


# TODO: add tests

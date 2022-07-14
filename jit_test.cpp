typedef __UINT8_TYPE__ uint8_t;
typedef __UINT16_TYPE__ uint16_t;
typedef __UINT32_TYPE__ uint32_t;
typedef __UINT64_TYPE__ uint64_t;
typedef __INT8_TYPE__ int8_t;
typedef __INT16_TYPE__ int16_t;
typedef __INT32_TYPE__ int32_t;
typedef __INT64_TYPE__ int64_t;

/// returns `v + inc` by jitting an addi instruction and executing it
/// requires .wtext section to be writable
extern "C" uint64_t jit_test(uint64_t v, int16_t inc) __attribute__((noinline, section(".wtext")));
extern "C" uint64_t jit_test(uint64_t v, int16_t inc) {
    register uint64_t r3 asm("r3");
    r3 = v;
    uint32_t instr = 0x38630000 | (uint16_t)inc; // addi 3, 3, inc
    asm("mflr 5\n\t"
        "bl 0f\n\t"
        "0: mflr 4\n\t"
        "addi 4, 4, 1f - 0b\n\t"
        "stw %1, 0(4)\n\t"
        "dcbf 0, 4\n\t"
        "sync\n\t"
        "icbi 0, 4\n\t"
        "isync\n\t"
        "1: addi 3, 3, 0x1234\n\t"
        "mtlr 5"
        : "+b"(r3) : "b"(instr) : "r4", "r5");
    return r3;
}

extern "C" uint64_t parse_hex(const char *s) __attribute__((noinline));
extern "C" uint64_t parse_hex(const char *s) {
    uint64_t retval = 0;
    bool negate = *s == '-';
    if(*s == '-' || *s == '+')
        s++;
    if(*s == '0' && (s[1] == 'x' || s[1] == 'X'))
        s += 2;
    if(!*s)
        return -1;
    for(; *s; s++) {
        uint64_t digit;
        if(*s >= '0' && *s <= '9')
            digit = *s - '0';
        else if(*s >= 'a' && *s <= 'f')
            digit = *s - 'a' + 0xA;
        else if(*s >= 'A' && *s <= 'F')
            digit = *s - 'A' + 0xA;
        else
            return -1;
        if(retval >= 1ULL << 60)
            return -1;
        retval <<= 4;
        retval += digit;
    }
    return retval;
}

extern "C" int main(int argc, char **argv) {
    uint64_t a = 1, b = 2;
    if(argc > 1)
        a = parse_hex(argv[1]);
    if(argc > 2)
        b = parse_hex(argv[2]);
    register long r3 asm("r3") = jit_test(a, b);
    register long r0 asm("r0") = 1; // exit
    asm volatile("sc" : : "r"(r0), "b"(r3));
}

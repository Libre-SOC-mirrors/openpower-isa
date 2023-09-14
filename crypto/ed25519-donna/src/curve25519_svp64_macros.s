    .machine libresoc
    .file      "curve25519_svp64_macros.s"

# Helper macros for assembly

# load word immediate for 32-bit constants
.macro  lwi rD, const
.if (\const >= -0x8000) && (\const <= 0x7fff)
    li      \rD, \const
.else
    lis     \rD, \const@ha
    ori     \rD, \rD, \const@l
.endif
.endm

# load double word immediate for 64-bit constants
.macro  ldi rD, const
.if (\const >= -0x80000000) && (\const <= 0x7fffffff)
    lwi      \rD, \const
.else
    # load high word into the high word of rD
    lis     \rD,\const@highest       # load msg bits 48-63 into rD bits 16-31
    ori     \rD,\rD,\const@higher    # load msg bits 32-47 into rD bits  0-15

    rldicr  \rD,\rD,32,31           # rotate r4's low word into rD's high word

    # load low word into the low word of rD
    oris    \rD,\rD,\const@h         # load msg bits 16-31 into rD bits 16-31
    ori     \rD,\rD,\const@l         # load msg bits  0-15 into rD bits  0-15
.endif
.endm

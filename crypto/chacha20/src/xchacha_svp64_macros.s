    .machine libresoc
    .file      "xchacha20_svp64_macros.s"

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

# This macro uses registers 8-21
.macro  quarterround_const _SHAPE0, _SHAPE1, _SHAPE2, _SHIFTS
    # load SHAPE0 indices
    ldi                 \_SHAPE0+0, 0x901090108000800
    ldi                 \_SHAPE0+1, 0xb030b030a020a02
    ldi                 \_SHAPE0+2, 0xb010b010a000a00
    ldi                 \_SHAPE0+3, 0x903090308020802
    # load SHAPE1 indices
    ldi                 \_SHAPE1+0, 0xd050d050c040c04
    ldi                 \_SHAPE1+1, 0xf070f070e060e06
    ldi                 \_SHAPE1+2, 0xc060c060f050f05
    ldi                 \_SHAPE1+3, 0xe040e040d070d07
    # load SHAPE2 indices
    ldi                 \_SHAPE2+0, 0x50d050d040c040c
    ldi                 \_SHAPE2+1, 0x70f070f060e060e
    ldi                 \_SHAPE2+2, 0x60c060c050f050f
    ldi                 \_SHAPE2+3, 0x40e040e070d070d
    #shift values
    ldi                 \_SHIFTS+0, 0x0000000c00000010
    ldi                 \_SHIFTS+1, 0x0000000700000008
.endm

# This macro uses registers 8-21
.macro  quarterround _x, _ctr, _VL, _SHAPE0, _SHAPE1, _SHAPE2, _SHIFTS
    mtctr	            \_ctr                           # Set up counter

    # set up VL=32 vertical-first, and SVSHAPEs 0-2
    # set VL/MAXVL first
    setvl               0, 0, 32, 0, 1, 1               # MAXVL=VL=32
    # set r22 from VL, set vertical-first
    setvl               \_VL, 0, 32, 1, 0, 1            # vertical-first mode
    # SHAPE0, used by sv.add starts at GPR #8
    svindex             \_SHAPE0/2, 0, 1, 3, 0, 1, 0    # SVSHAPE0, a
    # SHAPE1, used by sv.xor starts at GPR #12
    svindex             \_SHAPE1/2, 1, 1, 3, 0, 1, 0    # SVSHAPE1, b
    # SHAPE2, used by sv.rldcl starts at GPR #16
    svindex             \_SHAPE2/2, 2, 1, 3, 0, 1, 0    # SVSHAPE2, c
    # SHAPE3, used also by sv.rldcl to hold the shift values starts at GPR #20
    # The inner loop will do 32 iterations, but there are only 4 shift values, so we mod 4
    svshape2            0, 0, 3, 4, 0, 1                # SVSHAPE3, shift amount, mod 4

.outer:
    # outer loop begins here (standard CTR loop)
    setvl               \_VL, \_VL, 32, 1, 1, 0         # vertical-first, set VL from r22
    # inner loop begins here. add-xor-rotl32 with remap, step, branch
.inner:
    svremap             31, 1, 0, 0, 0, 0, 0            # RA=1, RB=0, RT=0 (0b01011)
    sv.add/w=32         *\_x, *\_x, *\_x
    svremap             31, 2, 0, 2, 2, 0, 0            # RA=2, RB=0, RS=2 (0b00111)
    sv.xor/w=32         *\_x, *\_x, *\_x
    svremap             31, 0, 3, 2, 2, 0, 0            # RA=2, RB=3, RS=2 (0b01110)
    sv.rldcl/w=32       *\_x, *\_x, *\_SHIFTS, 0
    # 16 is the destination containing the result of svstep.
    # it overlaps with SHAPE2 which is also 16. the first 8 indices
    # will get corrupted.
    svstep.             \_ctr, 1, 0                     # step to next in-regs element
    bc                  6, 3, .inner                    # svstep. Rc=1 loop-end-condition?
    # inner-loop done: outer loop standard CTR-decrement to setvl again
    bdnz	            .outer                          # Loop until CTR is zero
.endm

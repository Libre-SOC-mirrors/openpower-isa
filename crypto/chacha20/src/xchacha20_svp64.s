.set out_ptr, 3
.set in_ptr, 4
.set k_ptr, 5
.set ctr, 7
.set SHAPE0, 8
.set SHAPE1, 12 
.set SHAPE2, 16
.set SHIFTS, 20
.set x, 24

.macro  lwi rD, const
.if (\const >= -0x8000) && (\const <= 0x7fff)
    li      \rD, \const
.else
    lis     \rD, \const@ha
    ori     \rD, \rD, \const@l
.endif
.endm

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

    .machine libresoc
    .file	"xchacha20_svp64.s"
    .abiversion 2
    .section	".text"
    .align 2
    .globl  xchacha_hchacha20_svp64_real
    .type   xchacha_hchacha20_svp64_real, @function
xchacha_hchacha20_svp64_real:
.LFB0:
	.cfi_startproc
    # load x[0] = 0x61707865, x[1] = 0x3320646e
    ldi                 x+0, 0x3320646e61707865
    # load x[2] = 0x79622d32, x[3] = 0x6b206574
    ldi                 x+1, 0x6b20657479622d32
    # load SHAPE0 indices
    ldi                 SHAPE0+0, 0x901090108000800
    ldi                 SHAPE0+1, 0xb030b030a020a02
    ldi                 SHAPE0+2, 0xb010b010a000a00
    ldi                 SHAPE0+3, 0x903090308020802
    # load SHAPE1 indices
    ldi                 SHAPE1+0, 0xd050d050c040c04
    ldi                 SHAPE1+1, 0xf070f070e060e06
    ldi                 SHAPE1+2, 0xc060c060f050f05
    ldi                 SHAPE1+3, 0xe040e040d070d07
    # load SHAPE2 indices
    ldi                 SHAPE2+0, 0x50d050d040c040c
    ldi                 SHAPE2+1, 0x70f070f060e060e
    ldi                 SHAPE2+2, 0x60c060c050f050f
    ldi                 SHAPE2+3, 0x40e040e070d070d
    #shift values
    ldi                 SHIFTS+0, 0x0000000c00000010
    ldi                 SHIFTS+1, 0x0000000700000008

    # Load 8 values from k_ptr
    setvl	            0,0,4,0,1,1			    # Set VL to 8 elements
    sv.ld               *x+2, 0(k_ptr)

    # Load 4 values from in_ptr
    setvl	            0,0,2,0,1,1			    # Set VL to 4 elements
    sv.ld               *x+6, 0(in_ptr)

    # after this step, registers 16-32 hold the values that will be in the main loop
    # establish CTR for outer round count
    #li                  ctr, 10
    #mtctr	            ctr				        # Set up counter

    # outer loop begins here (standard CTR loop)
    # set up VL=32 vertical-first, and SVSHAPEs 0-2
    # vertical-first, set MAXVL (and r22)
    setvl               22, 0, 16, 1, 0, 1
    # SHAPE0, used by sv.add starts at GPR #8, need to offset those indices for x=24
    svindex             4, 0, 1, 3, 0, 1, 0     # SVSHAPE0, a
    # SHAPE1, used by sv.xor starts at GPR #12
    svindex             6, 1, 1, 3, 0, 1, 0     # SVSHAPE1, b
    # SHAPE2, used by sv.rldcl starts at GPR #16
    svindex             8, 2, 1, 3, 0, 1, 0     # SVSHAPE2, c
    # SHAPE3, used also by sv.rldcl to hold the shift values starts at GPR #20
    # The inner loop will do 16 iterations, but there are only 4 shift values, so we mod 4
    svshape2            0, 0, 3, 4, 0, 1        # SVSHAPE3, shift amount, mod 4
    
.outer:
    # outer loop begins here (standard CTR loop)
    setvl               22, 22, 16, 1, 1, 0     # vertical-first, set VL from r22
    # inner loop begins here. add-xor-rotl32 with remap, step, branch
.inner:
    svremap             31, 1, 0, 0, 0, 0, 0    # RA=1, RB=0, RT=0 (0b01011)
    sv.add/w=32         *x+24, *x+24, *x+24
    svremap             31, 2, 0, 2, 2, 0, 0    # RA=2, RB=0, RS=2 (0b00111)
    sv.xor/w=32         *x+24, *x+24, *x+24
    svremap             31, 0, 3, 2, 2, 0, 0    # RA=2, RB=3, RS=2 (0b01110)
    sv.rldcl/w=32       *x+24, *x+24, *SHIFTS, 0
    svstep.             16, 1, 0                # step to next in-regs element
    bc                  6, 3, .inner            # svstep. Rc=1 loop-end-condition?
    # inner-loop done: outer loop standard CTR-decrement to setvl again
    #bdnz	            .outer                  # Loop until CTR is zero

    # store x0-x3 directly to *out_ptr
	setvl	            0,0,2,0,1,1			    # Set VL to 4 elements
    sv.std              *x, 0(out_ptr)
    # store x12-x15 to *out_ptr + 16
    sv.std              *x+6, 16(out_ptr)
    blr
    .long 0
    .byte 0,0,0,0,0,3,0,0
    .cfi_endproc

.LFE0:
    .size	xchacha_hchacha20_svp64_real,.-xchacha_hchacha20_svp64_real
    .ident	"GCC: (Debian 8.3.0-6) 8.3.0"
    .section	.note.GNU-stack,"",@progbits

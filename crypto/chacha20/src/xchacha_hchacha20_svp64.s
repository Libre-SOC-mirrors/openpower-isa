    .machine libresoc
    .file      "xchacha_hchacha20_svp64.s"
    .abiversion 2
    .section   ".text"
    .align 2

    .include "xchacha_svp64_macros.s"

    .set out_ptr, 3
    .set in_ptr, 4
    .set k_ptr, 5
    .set ctr, 7
    .set x, 24
    .set SHAPE0, 8
    .set SHAPE1, 12 
    .set SHAPE2, 16
    .set SHIFTS, 20

    .globl  xchacha_hchacha20_svp64_real
    .type   xchacha_hchacha20_svp64_real, @function
xchacha_hchacha20_svp64_real:
	.cfi_startproc
    # load x[0] = 0x61707865, x[1] = 0x3320646e
    ldi                 x+0, 0x3320646e61707865
    # load x[2] = 0x79622d32, x[3] = 0x6b206574
    ldi                 x+1, 0x6b20657479622d32
    # Load 8 values from k_ptr
    setvl	            0,0,4,0,1,1			    # Set VL to 8 elements
    sv.ld               *x+2, 0(k_ptr)
    # Load 4 values from in_ptr
    setvl	            0,0,2,0,1,1			    # Set VL to 4 elements
    sv.ld               *x+6, 0(in_ptr)

    # Set up quarterround constants, SHAPE0, SHAPE1, SHAPE2, SHIFTS
    quarterround_const  SHAPE0, SHAPE1, SHAPE2, SHIFTS

    # establish CTR for outer round count and call quarterround macro
    li                  ctr, 10
    quarterround        x, ctr, SHAPE0, SHAPE1, SHAPE2, SHIFTS

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

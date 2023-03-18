    .machine libresoc
    .file      "xchacha20_svp64.s"
    .abiversion 2
    .section   ".text"
    .align 2

    .include "xchacha_svp64_macros.s"

    .set tmp, 2
    .set ctx_ptr, 3
    .set m_ptr, 4
    .set c_ptr, 5
    .set bytes, 6
    .set ctr, 7
    .set SHAPE0, 8
    .set SHAPE1, 12 
    .set SHAPE2, 16
    .set SHIFTS, 20
    .set VL, 22
    .set j, 24
    .set m, 32
    .set x, 40

    .globl  xchacha_encrypt_bytes_svp64_real
    .type   xchacha_encrypt_bytes_svp64_real, @function
xchacha_encrypt_bytes_svp64_real:
	.cfi_startproc

    # if bytes == 0, return
    cmplwi              bytes, 0
    beqlr

    # Load 16 x 32-bit values from ctx->input
    setvl	            0,0,8,0,1,1			    # Set VL to 8 elements
    sv.ld               *j, 0(ctx_ptr)

    # Set up quarterround constants, SHAPE0, SHAPE1, SHAPE2, SHIFTS
    quarterround_const  SHAPE0, SHAPE1, SHAPE2, SHIFTS
.loop:
    # Copy j[] to x[], 16 x 32-bit elements
    setvl               0,0,8,0,1,1
    sv.or               *x, *j, *j

    # find out how many bytes to load from m: min(bytes, 64), but need to count octets
    srdi                tmp, bytes, 3
    cmplwi              tmp, 8
    bgt                 .l1
    li                  tmp, 8
              
.l1:
    # Set ctr to min(64, bytes)
    ori                 ctr, tmp, 0

    # Load 64 bytes from m_ptr, 8 x 64-bit elements, set MAXVL=8
    setvl	            0,ctr,8,0,1,1
    sv.ld               *m, 0(m_ptr)

    # establish CTR for outer round count
    li                  ctr, 10
    # Call QuarterRound macro for CTR loops on x[]
    quarterround        x, ctr, VL, SHAPE0, SHAPE1, SHAPE2, SHIFTS

    # Add j[] to x[], 16 x 32-bit elements
    setvl	            0,0,16,0,1,1
    sv.add/w=32         *x, *x, *j

    # XOR x[] elements with m[], 16 x 32-bit elements
    sv.xor/w=32         *x, *x, *m

    # j12++; if (!j12) j13++;
    addi                j+6, j+6, 1             # j12 is in the 6th 64-bit register
    cmplwi              j+6, 0
    bne                 .l2                     # if j12 != 0 skip this
    ldi                 tmp, 0x100000000        # we have 2x32-bit values in the register, so need to add 1 << 32
    add                 j+6, j+6, tmp

.l2:
    # Store 8 x 64-bit from x[] to c_ptr
	setvl	            0,0,8,0,1,1
    sv.std              *x, 0(c_ptr)

    cmplwi              bytes, 64
    bgt                 .l5
.l3:
    bne                 .l4
    # find out how many bytes to load from m: min(bytes, 64), but need to count octets
    # TODO: properly store the bytes using elwidth
    srdi                tmp, bytes, 3
    addi                tmp, tmp, 1
    setvl               0,tmp,8,0,1,1
    sv.ld               *m, 0(c_ptr)

.l4:
    std                 j+6, 48(ctx_ptr)
    blr
.l5:
    subi                bytes, bytes, 64
    addi                c_ptr, c_ptr, 64
    addi                m_ptr, m_ptr, 64
    bl                  .loop

    .long 0
    .byte 0,0,0,0,0,3,0,0
    .cfi_endproc

.LFE0:
    .size	xchacha_encrypt_bytes_svp64_real,.-xchacha_encrypt_bytes_svp64_real
    .ident	"GCC: (Debian 8.3.0-6) 8.3.0"
    .section	.note.GNU-stack,"",@progbits

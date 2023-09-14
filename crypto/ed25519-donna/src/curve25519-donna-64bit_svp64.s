    .machine libresoc
    .file      "curve25519-donna-64bit_svp64.s"
    .abiversion 2
    .section   ".text"
    .align 2

    .include "curve25519_svp64_macros.s"

    .set out_ptr, 2
    .set in_ptr, 3
    .set j, 8

    .globl  curve25519_copy_svp64_asm
    .type   curve25519_copy_svp64_asm, @function
curve25519_copy_svp64_asm:
    .cfi_startproc

    # Load 5 x 64-bit values from in
    setvl	            0,0,5,0,1,1			    # Set VL to 5 elements
    sv.ld               *j, 0(in_ptr)
    sv.std              *j, 0(out_ptr)

    blr

    .long 0
    .cfi_endproc

.LFE0:
    .size	curve25519_copy_svp64_asm,.-curve25519_copy_svp64_asm
    .ident	"GCC: (Debian 8.3.0-6) 8.3.0"
    .section	.note.GNU-stack,"",@progbits

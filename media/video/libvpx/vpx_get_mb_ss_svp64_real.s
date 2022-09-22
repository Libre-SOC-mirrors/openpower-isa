.set in, 3
.set src, 10
.set prod, 50
.set sum, 4
.set ctr, 9


	.machine libresoc
	.file	"variancefuncs_svp64.c"
	.text
	.abiversion 2
	.section	".text"
	.align 2
	.globl vpx_get_mb_ss_svp64_real
	.type	vpx_get_mb_ss_svp64_real, @function
vpx_get_mb_ss_svp64_real:
.LFB0:
	.cfi_startproc
	# Set sum to zero
	li sum, 0				# Set sum to zero
	li ctr, 8				# Need 8 iterations of 32 elements
	mtctr ctr				# Set counter special register
	setvl 0,0,32,0,1,1			# Set VL to 32 elements
.L2:
	sv.lha	 	*src, 0(in)		# Load 32 ints from (in)
    # XXX these next two should be doable as "sv.maddld/mr sum, *src, *src, sum"
    # but we have to wait for an update to binutils
	# equivalent to: for (i = 0; i < 32; i++) vprod[i] = src[i] * src[i];
	sv.mulld 	*prod, *src, *src
	# equivalent to: for (i = 0; i < 32; i++) sum += prod[i];
	sv.add/mr	sum, *prod, sum
	addi in, in, 64				# Advance (in) pointer by 64 bytes
	bdnz .L2				# Loop until CTR is zero
	mr in, sum				# Set r3 to sum
	blr
	.long 0
	.byte 0,0,0,0,0,0,0,0
	.cfi_endproc
.LFE0:
	.size	vpx_get_mb_ss_svp64_real,.-vpx_get_mb_ss_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

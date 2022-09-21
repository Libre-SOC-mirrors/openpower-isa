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
	li sum, 0
	li ctr, 8
	mtctr ctr
	setvl 0,0,32,0,1,1			# Set VL to 64 elements
.L2:
	# Load 32 ints from (in)
	sv.lha	 	*src, 0(in)
	# equivalent to: for (i = 0; i < 32; i++) vprod[i] = src[i] * src[i];
	sv.mulld 	*prod, *src, *src
	# equivalent to: for (i = 0; i < 32; i++) sum += prod[i];
	sv.add/mr	sum, *prod, sum
	addi in, in, 64
#	rldicl in,ctr,0,32
	bdnz .L2
	li in, 0
	addi in, sum, 0
	blr
	.long 0
	.byte 0,0,0,0,0,0,0,0
	.cfi_endproc
.LFE0:
	.size	vpx_get_mb_ss_svp64_real,.-vpx_get_mb_ss_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

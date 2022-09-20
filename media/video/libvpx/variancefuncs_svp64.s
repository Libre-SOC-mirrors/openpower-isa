	.file	"variancefuncs_svp64.c"
	.abiversion 2
	.section	".text"
	.align 2
	.globl vpx_get_mb_ss_svp64_real
	.type	vpx_get_mb_ss_svp64_real, @function
vpx_get_mb_ss_svp64_real:
.LFB0:
	.cfi_startproc
	addi 10,3,-2
	li 3,0
	li 9,256
	mtctr 9
.L2:
	lhau 9,2(10)
	mullw 9,9,9
	add 9,9,3
	rldicl 3,9,0,32
	bdnz .L2
	blr
	.long 0
	.byte 0,0,0,0,0,0,0,0
	.cfi_endproc
.LFE0:
	.size	vpx_get_mb_ss_svp64_real,.-vpx_get_mb_ss_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

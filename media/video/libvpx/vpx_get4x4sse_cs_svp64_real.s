	.file	"vpx_get4x4sse_cs_svp64_real.c"
	.abiversion 2
	.section	".text"
	.align 2
	.globl vpx_get4x4sse_cs_svp64_real
	.type	vpx_get4x4sse_cs_svp64_real, @function
vpx_get4x4sse_cs_svp64_real:
.LFB0:
	.cfi_startproc
	addi 5,5,-1
	addi 3,3,3
	li 12,4
	li 8,0
.L2:
	addi 7,3,-4
	mr 11,5
	subf 9,7,3
	mtctr 9
.L3:
	lbzu 9,1(7)
	lbzu 10,1(11)
	subf 9,10,9
	mullw 9,9,9
	add 9,9,8
	extsw 8,9
	bdnz .L3
	addi 9,12,-1
	add 5,5,6
	add 3,3,4
	rldicl. 12,9,0,32
	bne 0,.L2
	rldicl 3,8,0,32
	blr
	.long 0
	.byte 0,0,0,0,0,0,0,0
	.cfi_endproc
.LFE0:
	.size	vpx_get4x4sse_cs_svp64_real,.-vpx_get4x4sse_cs_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

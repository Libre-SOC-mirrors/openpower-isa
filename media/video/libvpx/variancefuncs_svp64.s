.set in, 3
.set vin, 20
.set sum, 6
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
	addi 10, in ,-2
	li in, 0
	li sum, 0
	li ctr, 4
	mtctr ctr
	setvl 0,0,64,0,1,1			# Set VL to 64 elements
.L2:
	# Load 64 ints from (in)
	sv.lha	 	*vin, 0(in)
	# equivalent to: for (i = 0; i < 64; i++) sum += in[i] * in[i];
	sv.maddld 	sum, *vin, *vin, sum
	addi in, in, 16
	rldicl in,ctr,0,32
	bdnz .L2
	blr
	.long 0
	.byte 0,0,0,0,0,0,0,0
	.cfi_endproc
.LFE0:
	.size	vpx_get_mb_ss_svp64_real,.-vpx_get_mb_ss_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

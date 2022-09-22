.set src_ptr, 3
.set src_stride, 4
.set ref_ptr, 5
.set ref_stride, 6
.set sum, 7
.set src, 10
.set ref, 26
.set diff, 42
.set prod, 58
.set ctr, 9

	.machine libresoc
	.file	"vpx_get4x4sse_cs_svp64_real.c"
	.abiversion 2
	.section	".text"
	.align 2
	.globl vpx_get4x4sse_cs_svp64_real
	.type	vpx_get4x4sse_cs_svp64_real, @function
vpx_get4x4sse_cs_svp64_real:
.LFB0:
	.cfi_startproc
	# Set sum to zero
	li sum, 0				# Set sum to zero
	sldi	src_stride, src_stride, 1	# strides are for 16-bit elements
	sldi	ref_stride, ref_stride, 1	# we need to increase by bytes
	# Load 16 elements from src_ptr and ref_ptr, at groups of 4 with stride
	setvl	0,0,4,0,1,1			# Set VL to 4 elements
	sv.lha	*src, 0(src_ptr)		# Load 4 ints from (src_ptr)
	add 	src_ptr, src_ptr, src_stride	# Advance src_ptr by src_stride
	sv.lha 	*src + 4, 0(src_ptr)
	add 	src_ptr, src_ptr, src_stride
	sv.lha 	*src + 8, 0(src_ptr)
	add 	src_ptr, src_ptr, src_stride
	sv.lha 	*src + 12, 0(src_ptr)
	sv.lha	*ref, 0(ref_ptr)		# Load 4 ints from (ref_ptr)
	add 	ref_ptr, ref_ptr, ref_stride	# Advance ref_ptr by ref_stride
	sv.lha 	*ref + 4, 0(ref_ptr)
	add 	ref_ptr, ref_ptr, ref_stride
	sv.lha 	*ref + 8, 0(ref_ptr)
	add 	ref_ptr, ref_ptr, ref_stride
	sv.lha 	*ref + 12, 0(ref_ptr)

	# now our values are in consecutive registers and we can set VL to 16 elements
	setvl		0,0,16,0,1,1
	# equivalent to: for (i = 0; i < 16; i++) diff[i] = src[i] - ref[i];
	sv.subf		*diff, *src, *ref
	# equivalent to: for (i = 0; i < 16; i++) prod[i] = diff[i] * diff[i];
	sv.mulld 	*prod, *diff, *diff
	# equivalent to: for (i = 0; i < 16; i++) sum += prod[i];
	sv.add/mr	sum, *prod, sum
	mr 3, sum				# Set r3 to sum
	blr
	.long 0
	.byte 0,0,0,0,0,0,0,0
	.cfi_endproc
.LFE0:
	.size	vpx_get4x4sse_cs_svp64_real,.-vpx_get4x4sse_cs_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

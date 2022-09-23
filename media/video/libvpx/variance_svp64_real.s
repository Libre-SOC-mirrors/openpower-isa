.set src_ptr, 3
.set src_stride, 4
.set ref_ptr, 5
.set ref_stride, 6
.set width, 7
.set height, 8
.set sse_ptr, 9
.set sum_ptr, 10
.set sum, 11
.set sse, 12
.set ctr, 13
.set src_col, 14
.set ref_col, 15
.set row, 16
.set src, 20
.set ref, 36
.set diff, 52
.set prod, 68

	.machine libresoc
	.file	"variance_svp64_real.c"
	.abiversion 2
	.section	".text"
	.align 2
	.globl variance_svp64_real
	.type	variance_svp64_real, @function
variance_svp64_real:
.LFB0:
	.cfi_startproc
	# Set sum to zero
	li sum, 0				# Set sum to zero
	li sse, 0				# Set sse to zero
	mr row, height				# Set row to height
	sldi	src_stride, src_stride, 1	# strides are for 16-bit elements
	sldi	ref_stride, ref_stride, 1	# we need to increase by bytes
	srdi	ctr, width, 2
	mtctr	ctr
	setvl	0,0,4,0,1,1			# Set VL to 4 elements

.L1:	# outer loop: for (r=0; r < h; r++)

.L2:	# inner loop: for (c=0; c < w; c += 4)
	# Load 4 elements from src_ptr and ref_ptr, at groups of 4
	mr	src_col, src_ptr		# Temporary variables
	mr	ref_col, ref_ptr
	sv.lha	*src, 0(src_col)		# Load 4 ints from (src_ptr)
	sv.lha	*ref, 0(ref_col)		# Load 4 ints from (ref_ptr)
	addi	src_col, src_col, 8		# Increment src, ref by 8 bytes
	addi	ref_col, ref_col, 8

	# equivalent to: for (i = 0; i < 4; i++) diff[i] = src[i] - ref[i];
	sv.subf		*diff, *src, *ref
	# equivalent to: for (i = 0; i < 4; i++) prod[i] = diff[i] * diff[i];
	sv.mulld 	*prod, *diff, *diff
	# equivalent to: for (i = 0; i < 4; i++) sum += diff[i];
	sv.add/mr	sum, *diff, sum
	# equivalent to: for (i = 0; i < 4; i++) sum += diff[i];
	sv.add/mr	sse, *prod, sse

	bdnz .L2				# Loop until CTR is zero
	add 	src_ptr, src_ptr, src_stride	# Advance src_ptr by src_stride
	add 	ref_ptr, ref_ptr, ref_stride	# Advance ref_ptr by ref_stride

	subi row, row, 1			# Subtract 1 from row
	cmpwi cr1, row, 0			# Is row zero?
	bne cr1, .L1				# Go back to L1 if not done
	std sum, 0(sum_ptr)			# Set (sum_ptr) to sum
	std sse, 0(sse_ptr)			# Set (sum_ptr) to sum
	blr
	.long 0
	.byte 0,0,0,0,0,3,0,0
	.cfi_endproc
.LFE0:
	.size	variance_svp64_real,.-variance_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

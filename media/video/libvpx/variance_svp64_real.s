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
.set ref, 24
.set diff, 28
.set prod, 32

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
	li	sum, 0				# Set sum to zero
	li	sse, 0				# Set sse to zero
	li	row, 0				# Set row to zero
	sldi	src_stride, src_stride, 1	# strides are for 16-bit elements
	sldi	ref_stride, ref_stride, 1	# we need to increase by bytes
    # XXX this can go, no need to divide by 4
	srdi	width, width, 2			# We load groups of 4
    # XXX this to be moved inside (top of) L2 loop
	setvl	0,0,4,0,1,1			# Set VL to 4 elements

.L1:	# outer loop: for (r=0; r < h; r++)
	mr	src_col, src_ptr		# Temporary variables
	mr	ref_col, ref_ptr
	mr	ctr, width			# Set up CTR to width/4 -1 on each row
	mtctr	ctr				# Set up counter
.L2:	# inner loop: for (c=0; c < w; c += 4)
	# XXX setvl	30,0,4,0,1,1			# Set MAXVL=4, and r30=VL=MIN(CTR,MAXVL)
	# Load 4 elements from src_ptr and ref_ptr
	sv.lha	*src, 0(src_col)		# Load 4 ints from (src_ptr)
	sv.lha	*ref, 0(ref_col)		# Load 4 ints from (ref_ptr)

	# equivalent to: for (i = 0; i < 4; i++) diff[i] = src[i] - ref[i];
	sv.subf		*diff, *ref, *src
	# equivalent to: for (i = 0; i < 4; i++) prod[i] = diff[i] * diff[i];
	sv.mulld 	*prod, *diff, *diff
	# equivalent to: for (i = 0; i < 4; i++) sum += diff[i];
	sv.add/mr	sum, *diff, sum
	# equivalent to: for (i = 0; i < 4; i++) sse += diff[i]*diff[i];
	sv.add/mr	sse, *prod, sse

	addi	src_col, src_col, 8		# Increment src, ref by 8 bytes
	addi	ref_col, ref_col, 8
    # XXX replace with "sv.bc/all 16,*0,L2" which does "CTR -= VL"
	bdnz	.L2				# Loop until CTR is zero

	add 	src_ptr, src_ptr, src_stride	# Advance src_ptr by src_stride
	add 	ref_ptr, ref_ptr, ref_stride	# Advance ref_ptr by ref_stride
	addi	row, row, 1			# Add 1 to row
	cmpw	cr1, row, height		# Is row equal to height?
	bne	cr1, .L1			# Go back to L1 if not done
	std	sum, 0(sum_ptr)			# Set (sum_ptr) to sum
	std	sse, 0(sse_ptr)			# Set (sum_ptr) to sum
	blr
	.long 0
	.byte 0,0,0,0,0,3,0,0
	.cfi_endproc
.LFE0:
	.size	variance_svp64_real,.-variance_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

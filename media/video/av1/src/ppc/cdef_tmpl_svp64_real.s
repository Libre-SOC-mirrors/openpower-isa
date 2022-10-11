.set y, 1
.set x, 2

.set img_ptr, 3
.set stride, 4
.set var, 5
.set bd, 6		# bitdepth_min_8

.set cost, 7		# cost array, 8 elements
.set divt, 14		# div_table[8]
.set img, 24		# img array, 8x8 = 64 elements
.set psum, 88		# We will place the results of the psums here
.set tmp, 108	 	# temporary elements
.set tmp2, 116	 	# temporary elements


	.machine libresoc
	.file	"cdef_tmpl_svp64_real.c"
	.abiversion 2
	.section	".text"
	.align 2
	.globl cdef_find_dir_svp64_real
	.type	cdef_find_dir_svp64_real, @function
cdef_find_dir_svp64_real:
.L0:
	.cfi_startproc
	# Load div_table[7] array
        # div_table[7] = { 840, 420, 280, 210, 168, 140, 120 };
	li		divt+0, 840
	li		divt+1, 420
	li		divt+2, 280
	li		divt+3, 210
	li		divt+4, 168
	li		divt+5, 140
	li		divt+6, 120
	li		divt+7, 105			# Add 105 as element 8 of the divt table
							# saves having to do special case for it
	
.L1:
	# Load 8x8 8-bit elements from img_ptr in groups of 8 with stride
	setvl		0,0,8,0,1,1			# Set VL to 8 elements
	sv.lha		*img, 0(img_ptr)		# Load 8 ints from (img_ptr)
	add 		img_ptr, img_ptr, stride	# Advance img_ptr by stride
	sv.lha	 	*img + 8, 0(img_ptr)
	add 		img_ptr, img_ptr, stride
	sv.lha 		*img + 16, 0(img_ptr)
	add 		img_ptr, img_ptr, stride
	sv.lha 		*img + 24, 0(img_ptr)
	add 		img_ptr, img_ptr, stride
	sv.lha 		*img + 32, 0(img_ptr)
	add 		img_ptr, img_ptr, stride
	sv.lha 		*img + 40, 0(img_ptr)
	add 		img_ptr, img_ptr, stride
	sv.lha 		*img + 48, 0(img_ptr)
	add 		img_ptr, img_ptr, stride
	sv.lha 		*img + 56, 0(img_ptr)

	setvl		0,0,64,0,1,1			# Set VL to 64 elements
	sv.sraw		*img, *img, bd			# img[x] >> bitdepth_min_8
	sv.addi		*img, *img, -128		# px = (img[x] >> bitdepth_min_8) - 128

	# Zero psum registers for partial_sum_hv
	setvl		0,0,16,0,1,1			# Set VL to 16 elements
	sv.ori		*psum, 0, 0

	# First do the horizontal partial sums:
	# partial_sum_hv[0][y] += px;
	setvl		0,0,8,0,1,1			# Set VL to 8 elements
	sv.add/mr	psum+0, psum+0, *img+0
	sv.add/mr	psum+1, psum+1, *img+8
	sv.add/mr	psum+2, psum+2, *img+16
	sv.add/mr	psum+3, psum+3, *img+24
	sv.add/mr	psum+4, psum+4, *img+32
	sv.add/mr	psum+5, psum+5, *img+40
	sv.add/mr	psum+6, psum+6, *img+48
	sv.add/mr	psum+7, psum+7, *img+56

	# Next the vertical partial sums:
        # partial_sum_hv[1][x] += px;
	sv.add/mr	*psum+8, *psum+8, *img+0
	sv.add/mr	*psum+8, *psum+8, *img+8
	sv.add/mr	*psum+8, *psum+8, *img+16
	sv.add/mr	*psum+8, *psum+8, *img+24
	sv.add/mr	*psum+8, *psum+8, *img+32
	sv.add/mr	*psum+8, *psum+8, *img+40
	sv.add/mr	*psum+8, *psum+8, *img+48
	sv.add/mr	*psum+8, *psum+8, *img+56

	# Zero cost registers
	setvl		0,0,8,0,1,1			# Set VL to 8 elements
	sv.ori		*cost, 0, 0

        # cost[2] += partial_sum_hv[0][n] * partial_sum_hv[0][n];
	sv.maddld/mr	cost+2, *psum, *psum, cost+2
        # cost[6] += partial_sum_hv[1][n] * partial_sum_hv[1][n];
	sv.maddld/mr	cost+6, *psum+8, *psum+8, cost+6

	# cost[2] *= 105
	# cost[6] *= 105
	mulli		cost+2, cost+2, 105
	mulli		cost+6, cost+6, 105

	# We're done with partial_sum_hv values, we can reuse the registers
	# for partial_sum_diag
	# Zero psum registers for partial_sum_diag
	setvl		0,0,30,0,1,1			# Set VL to 30 elements
	sv.ori		*psum, 0, 0

	setvl		0,0,8,0,1,1			# Set VL to 8 elements
	# First row of diagonal partial sums:
	# partial_sum_diag[0][y + x] += px;
	sv.add/mr	*psum+0, *psum+0, *img+0
	sv.add/mr	*psum+1, *psum+1, *img+8
	sv.add/mr	*psum+2, *psum+2, *img+16
	sv.add/mr	*psum+3, *psum+3, *img+24
	sv.add/mr	*psum+4, *psum+4, *img+32
	sv.add/mr	*psum+5, *psum+5, *img+40
	sv.add/mr	*psum+6, *psum+6, *img+48
	sv.add/mr	*psum+7, *psum+7, *img+56

	# Second row of diagonal partial sums:
	# partial_sum_diag[1][7 + y - x] += px;
	sv.add/mr	*psum+15, *psum+15, *img+56
	sv.add/mr	*psum+16, *psum+16, *img+48
	sv.add/mr	*psum+17, *psum+17, *img+40
	sv.add/mr	*psum+18, *psum+18, *img+32
	sv.add/mr	*psum+19, *psum+19, *img+24
	sv.add/mr	*psum+20, *psum+20, *img+16
	sv.add/mr	*psum+21, *psum+21, *img+8
	sv.add/mr	*psum+22, *psum+22, *img+0
	# these were calculated correctly but in reverse order,
	# but since they're going to be used in a sum, order is not important.
 
	setvl		0,0,15,0,1,1			# Set VL to 15 elements
	sv.ori		*tmp, 0, 0

        # cost[0] += (partial_sum_diag[0][n]      * partial_sum_diag[0][n] +
        #             partial_sum_diag[0][14 - n] * partial_sum_diag[0][14 - n]) * d;
	# Produce squares of all values
	sv.maddld/mr	*tmp, *psum+0, *psum+0, *tmp
	# Handle the first 8 elements in order, *includes* partial_sum_diag[0][7]!
	#setvl		0,0,8,0,1,1			# Set VL to 8 elements
	#sv.mulld	*tmp, *tmp, *divt
	# Handle remaining 7 elements, in reverse order
	setvl		0,0,7,0,1,1			# Set VL to 7 elements
	sv.svstep/mrr	*tmp2, 6, 1
	svindex		29,0b1,7,0,0,0,0
	sv.ori		*tmp, *divt, 0
	#sv.mulld	*tmp, *tmp, *divt
	# Now sum those up to cost[0] element
	#setvl		0,0,15,0,1,1			# Set VL to 15 elements
	#sv.add/mr	cost+0, *tmp, cost+0

	# Similarly for cost[4]
	# cost[4] += (partial_sum_diag[1][n]      * partial_sum_diag[1][n] +
	#             partial_sum_diag[1][14 - n] * partial_sum_diag[1][14 - n]) * d;
	#sv.maddld/mr	*tmp, *psum+16, *psum+16, *tmp
	#sv.maddld/mr	*tmp, *psum+24, *psum+24, *tmp
	#sv.mulld	*tmp, *tmp, *divt
	#sv.add/mr	cost+4, *tmp, cost+4


	# Zero psum registers for partial_sum_alt, process half of 44
	#setvl		0,0,22,0,1,1			# Set VL to 22 elements
	#sv.ori		psum, 0, 0

	# First row of alt partial sums:
	# partial_sum_alt [0][y + (x >> 1)] += px;
	# These are essentially calculated the following way:
	# horiz axis: x, vert axis: y, quantity of y + (x>>1):
	# 
	# |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 0 | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
	# | 1 | 1 | 1 | 2 | 2 | 3 | 3 | 4 | 4 |
	# | 2 | 2 | 2 | 3 | 3 | 4 | 4 | 5 | 5 |
	# | 3 | 3 | 3 | 4 | 4 | 5 | 5 | 6 | 6 |
	# | 4 | 4 | 4 | 5 | 5 | 6 | 6 | 7 | 7 |
	# | 5 | 5 | 5 | 6 | 6 | 7 | 7 | 8 | 8 |
	# | 6 | 6 | 6 | 7 | 7 | 8 | 8 | 9 | 9 |
	# | 7 | 7 | 7 | 8 | 8 | 9 | 9 | a | a |
	#
	# We calculate this in a similar manner to the diagonal
	# partial sums, but first we have to do pair-wise addition
	# on all the elements of the img matrix:
	#setvl		0,0,64,0,1,1			# Set VL to 64 elements
	#svstep		2
	#sv.add		*img, *img, *img+1

	#setvl		0,0,8,0,1,1			# Set VL to 8 elements
	#sv.add		*psum+0, *psum+0, *img+0
	#sv.add		*psum+0, *psum+0, *img+1
	#sv.add		*psum+1, *psum+1, *img+8
	#sv.add		*psum+1, *psum+1, *img+9


	#setvl		0,0,10,0,1,1			# Set VL to 2 elements
	#sv.add/mr	*psum, *psum, *psum+1
# 


	blr
	.long 0
	.byte 0,0,0,0,0,0,0,0
	.cfi_endproc
.LFE27:
	.size	cdef_find_dir_svp64_real,.-cdef_find_dir_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

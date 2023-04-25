.set img_ptr, 3
.set stride, 4
.set var, 5
.set bd, 6		# bitdepth_min_8

.set pred, 3		# predicate for last stage, reuse r3

.set ptr_copy, 7	# copy of img_ptr
.set ptr_orig, 2	# another one

.set max, 2		# max result
.set retval, 3		# return value

.set divt, 8		# div_table[15]
.set cost, 24		# cost array, 8 elements
.set img, 32		# img array, 8x8 = 64 elements
.set psum, 96		# We will place the results of the psums here
.set psum_alt, 64	# reuse img when done with last stage


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
	# Load div_table array, originally it is
        # div_table[7] = { 840, 420, 280, 210, 168, 140, 120 };
	# however, to make calculations easier, we add the same elements in reverse and 105 in middle
	# and just set VL=15
	li			divt+0, 840
	li			divt+1, 420
	li			divt+2, 280
	li			divt+3, 210
	li			divt+4, 168
	li			divt+5, 140
	li			divt+6, 120
	li			divt+7, 105
	li			divt+8, 120
	li			divt+9, 140
	li			divt+10, 168
	li			divt+11, 210
	li			divt+12, 280
	li			divt+13, 420
	li			divt+14, 840

	mr			ptr_copy, img_ptr
	mr			ptr_orig, img_ptr
	
.L1:
	# Load 8x8 8-bit elements from ptr_copy in groups of 8 with stride
	setvl			0,0,8,0,1,1			# Set VL to 8 elements
	sv.lha			*img, 0(ptr_copy)		# Load 8 ints from (ptr_copy)
	add 			ptr_copy, ptr_copy, stride	# Advance ptr_copy by stride
	sv.lha	 		*img + 8, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 16, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 24, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 32, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 40, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 48, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 56, 0(ptr_copy)

	setvl			0,0,64,0,1,1			# Set VL to 64 elements
	sv.sraw			*img, *img, bd			# img[x] >> bitdepth_min_8
	sv.addi			*img, *img, -128		# px = (img[x] >> bitdepth_min_8) - 128

	# Zero psum registers for partial_sum_hv
	setvl			0,0,16,0,1,1			# Set VL to 16 elements
	sv.ori			*psum, 0, 0

	# First do the horizontal partial sums:
	# partial_sum_hv[0][y] += px;
	setvl			0,0,8,0,1,1			# Set VL to 8 elements
	sv.add/mr		psum+0, psum+0, *img+0
	sv.add/mr		psum+1, psum+1, *img+8
	sv.add/mr		psum+2, psum+2, *img+16
	sv.add/mr		psum+3, psum+3, *img+24
	sv.add/mr		psum+4, psum+4, *img+32
	sv.add/mr		psum+5, psum+5, *img+40
	sv.add/mr		psum+6, psum+6, *img+48
	sv.add/mr		psum+7, psum+7, *img+56

	# Next the vertical partial sums:
        # partial_sum_hv[1][x] += px;
	sv.add/mr		*psum+8, *psum+8, *img+0
	sv.add/mr		*psum+8, *psum+8, *img+8
	sv.add/mr		*psum+8, *psum+8, *img+16
	sv.add/mr		*psum+8, *psum+8, *img+24
	sv.add/mr		*psum+8, *psum+8, *img+32
	sv.add/mr		*psum+8, *psum+8, *img+40
	sv.add/mr		*psum+8, *psum+8, *img+48
	sv.add/mr		*psum+8, *psum+8, *img+56

	# Zero cost registers
	setvl			0,0,8,0,1,1			# Set VL to 8 elements
	sv.ori			*cost, 0, 0

        # cost[2] += partial_sum_hv[0][n] * partial_sum_hv[0][n];
	sv.maddld/mr		cost+2, *psum, *psum, cost+2
        # cost[6] += partial_sum_hv[1][n] * partial_sum_hv[1][n];
	sv.maddld/mr		cost+6, *psum+8, *psum+8, cost+6

	# cost[2] *= 105
	# cost[6] *= 105
	mulli			cost+2, cost+2, 105
	mulli			cost+6, cost+6, 105

	# We're done with partial_sum_hv values, we can reuse the registers
	# for partial_sum_diag
	# Zero psum registers for partial_sum_diag
	setvl			0,0,30,0,1,1			# Set VL to 30 elements
	sv.ori			*psum, 0, 0

	setvl		0,0,8,0,1,1			# Set VL to 8 elements
	# First row of diagonal partial sums:
	# partial_sum_diag[0][y + x] += px;
	sv.add/mr		*psum+0, *psum+0, *img+0
	sv.add/mr		*psum+1, *psum+1, *img+8
	sv.add/mr		*psum+2, *psum+2, *img+16
	sv.add/mr		*psum+3, *psum+3, *img+24
	sv.add/mr		*psum+4, *psum+4, *img+32
	sv.add/mr		*psum+5, *psum+5, *img+40
	sv.add/mr		*psum+6, *psum+6, *img+48
	sv.add/mr		*psum+7, *psum+7, *img+56

	# Second row of diagonal partial sums:
	# partial_sum_diag[1][7 + y - x] += px;
	sv.add/mr		*psum+15, *psum+15, *img+56
	sv.add/mr		*psum+16, *psum+16, *img+48
	sv.add/mr		*psum+17, *psum+17, *img+40
	sv.add/mr		*psum+18, *psum+18, *img+32
	sv.add/mr		*psum+19, *psum+19, *img+24
	sv.add/mr		*psum+20, *psum+20, *img+16
	sv.add/mr		*psum+21, *psum+21, *img+8
	sv.add/mr		*psum+22, *psum+22, *img+0
	# these were calculated correctly but in reverse order,
	# but since they're going to be used in a sum, order is not important.
 
        # cost[0] += (partial_sum_diag[0][n]      * partial_sum_diag[0][n] +
        #             partial_sum_diag[0][14 - n] * partial_sum_diag[0][14 - n]) * d;
	# Produce squares of all values
	setvl			0,0,15,0,1,1			# Set VL to 15 elements
	sv.mulld		*psum+0, *psum+0, *psum+0
	sv.mulld		*psum+0, *psum+0, *divt
	sv.add/mr		cost+0, *psum+0, cost+0

	# Similarly for cost[4]
	# cost[4] += (partial_sum_diag[1][n]      * partial_sum_diag[1][n] +
	#             partial_sum_diag[1][14 - n] * partial_sum_diag[1][14 - n]) * d;
	sv.mulld		*psum+15, *psum+15, *psum+15
	sv.mulld		*psum+15, *psum+15, *divt
	sv.add/mr		cost+4, *psum+15, cost+4

	# First row of alt partial sums:
	# partial_sum_alt [0][y + (x >> 1)] += px;
	# These are essentially calculated the following way:
	# horiz axis: x, vert axis: y, quantity of y + (x>>1):
	#
	# We calculate this in a similar manner to the diagonal
	# partial sums, but first we have to do pair-wise addition
	# on all the elements of the img matrix, compressing the rows
	# to half size in the process
	#
	# 
	# |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |    |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | a |
	# | 0 | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |    | 0 | 0 | 1 | 2 | 3 |
	# | 1 | 1 | 1 | 2 | 2 | 3 | 3 | 4 | 4 |    | 1 |   | 1 | 2 | 3 | 4 |
	# | 2 | 2 | 2 | 3 | 3 | 4 | 4 | 5 | 5 |    | 2 |       | 2 | 3 | 4 | 5 |
	# | 3 | 3 | 3 | 4 | 4 | 5 | 5 | 6 | 6 | -> | 3 |           | 3 | 4 | 5 | 6 |
	# | 4 | 4 | 4 | 5 | 5 | 6 | 6 | 7 | 7 |    | 4 |               | 4 | 5 | 6 | 7 |
	# | 5 | 5 | 5 | 6 | 6 | 7 | 7 | 8 | 8 |    | 5 |                   | 5 | 6 | 7 | 8 |
	# | 6 | 6 | 6 | 7 | 7 | 8 | 8 | 9 | 9 |    | 6 |                       | 6 | 7 | 8 | 9 |
	# | 7 | 7 | 7 | 8 | 8 | 9 | 9 | a | a |    | 7 |                           | 7 | 8 | 9 | a |
	#
	setvl			0,0,16,0,1,1			# Set VL to 16 elements
	ori             	pred, 0, 0b0101010101010101
	sv.add/sm=r3		*psum+0, *img, *img+1
	sv.add/sm=r3		*psum+16, *img+16, *img+17
	#Copy the even-numbered registers only
	sv.ori/sm=r3		*img+0, *psum+0, 0
	sv.ori/sm=r3		*img+8, *psum+16, 0
	# Process the next 32 elements
	sv.add/sm=r3		*psum+0, *img+32, *img+33
	sv.add/sm=r3		*psum+16, *img+48, *img+49
	# Copy their sums (again even-numbered registers only)
	sv.ori/sm=r3		*img+16, *psum+0, 0
	sv.ori/sm=r3		*img+24, *psum+16, 0
	
	# clear registers to hold the values
	setvl			0,0,11,0,1,1			# Set VL to 22 elements
	sv.ori			*psum_alt, 0, 0

	setvl			0,0,4,0,1,1			# Set VL to 4 elements
	sv.add			*psum_alt+0, *psum_alt+0, *img+0
	sv.add			*psum_alt+1, *psum_alt+1, *img+4
	sv.add			*psum_alt+2, *psum_alt+2, *img+8
	sv.add			*psum_alt+3, *psum_alt+3, *img+12
	sv.add			*psum_alt+4, *psum_alt+4, *img+16
	sv.add			*psum_alt+5, *psum_alt+5, *img+20
	sv.add			*psum_alt+6, *psum_alt+6, *img+24
	sv.add			*psum_alt+7, *psum_alt+7, *img+28

	# We need to reshape div_table to ease calculations:
	# The elements 3 - 8 will be multiplied by 105
	# and elements 0-3 and 8-10 will be multiplied by 420, 210, 140, resp,
	# so 
	li			divt+0, 420
	li			divt+1, 210
	li			divt+2, 140
	setvl			0,0,5,0,1,1			# Set VL to 5 elements
	sv.ori			*divt+3, 0, 105
	li			divt+8, 140
	li			divt+9, 210
	li			divt+10, 420

	# Now the following is equivalent to:
	# for (int m = 0; m < 5; m++)
	#   cost[1] += partial_sum_alt[0][3 + m] * partial_sum_alt[0][3 + m];
        # cost[1] *= 105;
	# for (int m = 0; m < 3; m++) {
        #   const int d = div_table[2 * m + 1];
        #   cost[1] += (partial_sum_alt[0][m]      * partial_sum_alt[0][m] +
        #               partial_sum_alt[0][10 - m] * partial_sum_alt[0][10 - m]) * d;
	setvl			0,0,11,0,1,1			# Set VL to 11 elements
	sv.mulld		*psum_alt+0, *psum_alt+0, *psum_alt+0
	sv.mulld		*psum_alt+0, *psum_alt+0, *divt
	sv.add/mr		cost+1, *psum_alt+0, cost+1
 
	# Next row of partial_sum_alts, 
	# partial_sum_alt [1][3 + y - (x >> 1)] += px;
	#
	# |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |    |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | a |
	# | 0 | 3 | 3 | 2 | 2 | 1 | 1 | 0 | 0 |    | 0 |                           | 3 | 2 | 1 | 0 |
	# | 1 | 4 | 4 | 3 | 3 | 2 | 2 | 1 | 1 |    | 1 |                       | 4 | 3 | 2 | 1 |
	# | 2 | 5 | 5 | 4 | 4 | 3 | 3 | 2 | 2 |    | 2 |                   | 5 | 4 | 3 | 2 |
	# | 3 | 6 | 6 | 5 | 5 | 4 | 4 | 3 | 3 | -> | 3 |               | 6 | 5 | 4 | 3 |
	# | 4 | 7 | 7 | 6 | 6 | 5 | 5 | 4 | 4 |    | 4 |           | 7 | 6 | 5 | 4 |
	# | 5 | 8 | 8 | 7 | 7 | 6 | 6 | 5 | 5 |    | 5 |       | 8 | 7 | 6 | 5 |
	# | 6 | 9 | 9 | 8 | 8 | 7 | 7 | 6 | 6 |    | 6 |   | 9 | 8 | 7 | 6 |
	# | 7 | a | a | 9 | 9 | 8 | 8 | 7 | 7 |    | 7 | a | 9 | 8 | 7 |

	setvl			0,0,32,0,1,1			# clear everything
	sv.ori			*96, 0, 0

	# Same method, unfortunately now we have to load img again
	# With elwidth and subvl we could pack the data to avoid any loads whatsever
	# Load 8x8 8-bit elements from ptr_copy in groups of 8 with stride
	mr			ptr_copy, ptr_orig
	setvl			0,0,8,0,1,1			# Set VL to 8 elements
	sv.lha			*img, 0(ptr_copy)		# Load 8 ints from (ptr_copy)
	add 			ptr_copy, ptr_copy, stride	# Advance ptr_copy by stride
	sv.lha	 		*img + 8, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 16, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 24, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 32, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 40, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 48, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 56, 0(ptr_copy)

	setvl			0,0,64,0,1,1			# Set VL to 64 elements
	sv.sraw			*img, *img, bd			# img[x] >> bitdepth_min_8
	sv.addi			*img, *img, -128		# px = (img[x] >> bitdepth_min_8) - 128

	setvl			0,0,16,0,1,1			# Set VL to 16 elements
	ori             	pred, 0, 0b0101010101010101
	sv.add/sm=r3		*psum+0, *img, *img+1
	sv.add/sm=r3		*psum+16, *img+16, *img+17
	#Copy the even-numbered registers only
	sv.ori/sm=r3		*img+0, *psum+0, 0
	sv.ori/sm=r3		*img+8, *psum+16, 0
	# Process the next 32 elements
	sv.add/sm=r3		*psum+0, *img+32, *img+33
	sv.add/sm=r3		*psum+16, *img+48, *img+49
	# Copy their sums (again even-numbered registers only)
	sv.ori/sm=r3		*img+16, *psum+0, 0
	sv.ori/sm=r3		*img+24, *psum+16, 0

	# clear registers to hold the values
	setvl			0,0,11,0,1,1			# Set VL to 11 elements
	sv.ori			*psum_alt, 0, 0

	setvl			0,0,4,0,1,1			# Set VL to 4 elements
	sv.add			*psum_alt+7, *psum_alt+7, *img+0
	sv.add			*psum_alt+6, *psum_alt+6, *img+4
	sv.add			*psum_alt+5, *psum_alt+5, *img+8
	sv.add			*psum_alt+4, *psum_alt+4, *img+12
	sv.add			*psum_alt+3, *psum_alt+3, *img+16
	sv.add			*psum_alt+2, *psum_alt+2, *img+20
	sv.add			*psum_alt+1, *psum_alt+1, *img+24
	sv.add			*psum_alt+0, *psum_alt+0, *img+28

	# Now the following is equivalent to:
	# for (int m = 0; m < 5; m++)
	#   cost[3] += partial_sum_alt[1][3 + m] * partial_sum_alt[1][3 + m];
        # cost[3] *= 105;
	# for (int m = 0; m < 3; m++) {
        #   const int d = div_table[2 * m + 1];
        #   cost[3] += (partial_sum_alt[1][m]      * partial_sum_alt[1][m] +
        #               partial_sum_alt[1][10 - m] * partial_sum_alt[1][10 - m]) * d;
	setvl			0,0,11,0,1,1			# Set VL to 11 elements
	sv.mulld		*psum_alt+0, *psum_alt+0, *psum_alt+0
	sv.mulld		*psum_alt+0, *psum_alt+0, *divt
	sv.add/mr		cost+3, *psum_alt+0, cost+3

	#setvl			0,0,64,0,1,1			# clear everything
	#sv.ori			*img, 0, 0
	#setvl			0,0,32,0,1,1			# clear everything
	#sv.ori			*96, 0, 0

	# Next row of partial_sum_alts, 
	# partial_sum_alt [2][3 - (y >> 1) +  x      ] += px;
	#
	# |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |    |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | a |
	# | 0 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | a |    | 0 |           | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 1 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | a |    | 1 |           | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 2 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |    | 2 |       | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 3 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | -> | 3 |       | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 4 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |    | 4 |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 5 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |    | 5 |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 6 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |    | 6 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 7 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |    | 7 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |

	# We calculate this in a similar manner to the diagonal
	# partial sums, but first we have to do pair-wise addition, this time across rows
	# on all the elements of the img matrix, compressing the columns
	# to half size in the process

	# Similar method, unfortunately now we have to load img again
	# With elwidth and subvl we could pack the data to avoid any loads whatsever
	# Load 8x8 8-bit elements from ptr_copy in groups of 8 with stride
	mr			ptr_copy, ptr_orig
	setvl			0,0,8,0,1,1			# Set VL to 8 elements
	sv.lha			*img, 0(ptr_copy)		# Load 8 ints from (ptr_copy)
	add 			ptr_copy, ptr_copy, stride	# Advance ptr_copy by stride
	sv.lha	 		*img + 8, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 16, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 24, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 32, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 40, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 48, 0(ptr_copy)
	add 			ptr_copy, ptr_copy, stride
	sv.lha 			*img + 56, 0(ptr_copy)

	setvl			0,0,64,0,1,1			# Set VL to 64 elements
	sv.sraw			*img, *img, bd			# img[x] >> bitdepth_min_8
	sv.addi			*img, *img, -128		# px = (img[x] >> bitdepth_min_8) - 128

	# clear registers to hold the values
	setvl			0,0,11,0,1,1			# Set VL to 11 elements
	sv.ori			*psum, 0, 0

	setvl			0,0,8,0,1,1			# Set VL to 16 elements
	# sum row 1 & 2, index +3
	sv.add			*psum+3, *psum+3, *img+0
	sv.add			*psum+3, *psum+3, *img+8
	# sum row 2 & 3, index +2
	sv.add			*psum+2, *psum+2, *img+16
	sv.add			*psum+2, *psum+2, *img+24
	# sum row 4 & 5, index +1
	sv.add			*psum+1, *psum+1, *img+32
	sv.add			*psum+1, *psum+1, *img+40
	# sum row 6 & 7, index +0
	sv.add			*psum+0, *psum+0, *img+48
	sv.add			*psum+0, *psum+0, *img+56

	# Now the following is equivalent to:
	# for (int m = 0; m < 5; m++)
	#   cost[5] += partial_sum_alt[2][3 + m] * partial_sum_alt[2][3 + m];
        # cost[5] *= 105;
	# for (int m = 0; m < 3; m++) {
        #   const int d = div_table[2 * m + 1];
        #   cost[5] += (partial_sum_alt[2][m]      * partial_sum_alt[2][m] +
        #               partial_sum_alt[2][10 - m] * partial_sum_alt[2][10 - m]) * d;
	setvl			0,0,11,0,1,1			# Set VL to 11 elements
	sv.mulld		*psum+0, *psum+0, *psum+0
	sv.mulld		*psum+0, *psum+0, *divt
	sv.add/mr		cost+5, *psum+0, cost+5

	# Next row of partial_sum_alts, 
	# partial_sum_alt [3][ (y >> 1) +  x      ] += px;
	#
	# |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |    |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | a |
	# | 0 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |    | 0 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |    | 1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 2 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |    | 2 |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 3 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | -> | 3 |   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 4 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |    | 4 |       | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 5 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |    | 5 |       | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 6 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | a |    | 6 |           | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
	# | 7 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | a |    | 7 |           | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |

	# This calculation is similar to the previous, and we have enough registers available,
	# we don't have to reload img.

	setvl			0,0,11,0,1,1			# Set VL to 11 elements
	sv.ori			*psum, 0, 0

	setvl			0,0,8,0,1,1			# Set VL to 8 elements
	# sum row 1 & 2, index +0
	sv.add			*psum+0, *psum+0, *img+0
	sv.add			*psum+0, *psum+0, *img+8
	# sum row 2 & 3, index +1
	sv.add			*psum+1, *psum+1, *img+16
	sv.add			*psum+1, *psum+1, *img+24
	# sum row 4 & 5, index +2
	sv.add			*psum+2, *psum+2, *img+32
	sv.add			*psum+2, *psum+2, *img+40
	# sum row 6 & 7, index +3
	sv.add			*psum+3, *psum+3, *img+48
	sv.add			*psum+3, *psum+3, *img+56

	# Now the following is equivalent to:
	# for (int m = 0; m < 5; m++)
	#   cost[7] += partial_sum_alt[3][3 + m] * partial_sum_alt[3][3 + m];
        # cost[7] *= 105;
	# for (int m = 0; m < 3; m++) {
        #   const int d = div_table[2 * m + 1];
        #   cost[7] += (partial_sum_alt[3][m]      * partial_sum_alt[3][m] +
        #               partial_sum_alt[3][10 - m] * partial_sum_alt[3][10 - m]) * d;
	setvl			0,0,11,0,1,1			# Set VL to 11 elements
	sv.mulld		*psum+0, *psum+0, *psum+0
	sv.mulld		*psum+0, *psum+0, *divt
	sv.add/mr		cost+7, *psum+0, cost+7

	mr			max, cost+5
	setvl			0,0,8,0,1,1			# Set VL to 8 elements
	#sv.minmax/mr		max, max, *cost, 3 # MMM=maxs
	sv.cmp			0, 0, *cost, max
	svstep			retval, 5, 1
#	sv.addi/m=eq		retval,*,0
	blr
	.long 0
	.byte 0,0,0,0,0,0,0,0
	.cfi_endproc
.LFE27:
	.size	cdef_find_dir_svp64_real,.-cdef_find_dir_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

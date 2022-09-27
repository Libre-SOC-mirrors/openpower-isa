.set in, 3
.set out, 4
.set pitch, 5
.set c_2217, 6
.set c_5352, 7
.set c_7500, 9
.set c_12000, 11
.set c_51000, 12
.set pred, 10
.set ip, 16
.set t, 32
.set t2, 50 
.set t3, 70
.set op, 90

	.machine libresoc
	.file	"vp8_dct4x4_real.c"
	.abiversion 2
	.section	".text"
	.align 2
	.globl vp8_short_fdct4x4_svp64_real
	.type	vp8_short_fdct4x4_svp64_real, @function
vp8_short_fdct4x4_svp64_real:
.LFB0:
	.cfi_startproc
	li			c_51000, 25500
	sldi			c_51000, c_51000, 1		# c_51000 = 51000
	setvl			0,0,16,0,1,1			# Set VL to 16 elements
	sv.lha	 		*ip, 0(in)			# Load 4 ints from (in)

	ori			pred, 0, 0b0001000100010001
	sv.add/dm=r10		*t, *ip, *ip+3			# a1 = ip[0] + ip[3]
	sv.add/dm=r10		*t+1, *ip+1, *ip+2		# b1 = ip[1] + ip[2]
	sv.subf/dm=r10		*t+2, *ip+2, *ip+1		# c1 = ip[1] - ip[2]
	sv.subf/dm=r10		*t+3, *ip+3, *ip		# d1 = ip[0] - ip[3]
	sv.mulli		*t, *t, 8			# a1 *= 8, b1 *= 8, c1 *= 8, d1 *= 8

	sv.add/dm=r10		*op, *t, *t+1			# op[0] = a1 + b1;
	sv.subf/dm=r10		*op+2, *t+1, *t			# op[2] = a1 - b1;

	# Calculate c1 * 2217, c1 *5352, d1 * 2217 and d1 * 5352
	ori			pred, 0, 0b1100110011001100
	sv.mulli/m=r10		*t2, *t, 2217			# t2 has c1 * 2217, d1 * 2217
	sv.mulli/m=r10		*t3, *t, 5352 			# t3 has c1 * 5352, d1 * 5352

	ori			pred, 0, 0b0010001000100010
	# op[1] = (c1 * 2217 + d1 * 5352 + 14500)
	sv.add/m=r10		*op, *t2+1, *t3+2		# c1 * 2217 + d1 * 5352
	sv.addi/m=r10		*op, *op, 14500			# + 14500
	
	ori			pred, 0, 0b0100010001000100
	# op[3] = (d1 * 2217 - c1 * 5352 + 7500)
	sv.subf/m=r10		*op+1, *t3, *t2+1		# - c1 * 5352 + d1 * 2127
	sv.addi/m=r10		*op+1, *op+1, 7500		# + 7500

	ori			pred, 0, 0b1010101010101010
	sv.rldicl/m=r10		*op, *op, 52, 12		# op[1] >>= 12, op[3] >>= 12

	# column-wise DCT
	ori			pred, 0, 0b0000000000001111
	sv.add/m=r10		*t, *op, *op+12			# a1 = ip[0] + ip[12]
	sv.add/m=r10		*t+4, *op+4, *op+8		# b1 = ip[4] + ip[8]
	sv.subf/m=r10		*t+8, *op+8, *op+4		# c1 = ip[4] - ip[8]
	sv.subf/m=r10		*t+12, *op+12, *op		# d1 = ip[0] - ip[12]

	# op[0] = (a1 + b1 + 7) >> 4
	sv.add/m=r10		*op, *t, *t+4			# op[0] = a1 + b1
	sv.addi/m=r10		*op, *op, 7			# op[0] += 7

	# op[8] = (a1 - b1 + 7) >> 4
	sv.subf/m=r10		*op+8, *t+4, *t			# op[8] = a1 - b1
	sv.addi/m=r10		*op+8, *op+8, 7			# op[8] += 7

	ori			pred, 0, 0b0000111100001111
	sv.rldicl/m=r10		*op, *op, 60, 4			# op[0] >>= 4, op[8] >>= 4

	# Calculate c1 * 2217, c1 *5352, d1 * 2217 and d1 * 5352
	ori			pred, 0, 0b1111111100000000
	sv.mulli/m=r10		*t2, *t, 2217			# t2 has c1 * 2217, d1 * 2217
	sv.mulli/m=r10		*t3, *t, 5352 			# t3 has c1 * 5352, d1 * 5352

	# op[4] = ((c1 * 2217 + d1 * 5352 + 12000)
	ori			pred, 0, 0b0000000011110000
	sv.add/m=r10		*op, *t2+4, *t3+8		# c1 * 2217 + d1 * 5352
	sv.addi/m=r10		*op, *op, 12000			# + 12000
	
	# op[12] = (d1 * 2217 - c1 * 5352 + 51000)
	ori			pred, 0, 0b1111000000000000
	sv.subf/m=r10		*op, *t3-4, *t2			# - c1 * 5352 + d1 * 2127
	sv.add/m=r10		*op, *op, c_51000		# + 51000

	ori			pred, 0, 0b1111000011110000
	sv.rldicl/m=r10		*op, *op, 48, 16		# op[4] >>= 16, op[12] >= 16

	# op[4] += (d1 != 0)
	#ori			pred, 0, 0b0000000011110000
	setvl			0,0,4,0,1,1			# Set VL to 16 elements
	sv.cmpi			*cr0, 0, *t+12, 1
	sv.addi/m=ne		*op+4, *op+4, 1

	# store to buffer
	setvl			0,0,16,0,1,1			# Set VL to 16 elements
	sv.sth			*op, 0(out)
	blr
	.long 0
	.byte 0,0,0,0,128,1,0,1
	.cfi_endproc
.LFE0:
	.size	vp8_short_fdct4x4_svp64_real,.-vp8_short_fdct4x4_svp64_real
	.ident	"GCC: (Debian 8.3.0-6) 8.3.0"
	.section	.note.GNU-stack,"",@progbits

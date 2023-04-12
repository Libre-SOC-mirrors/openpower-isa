# # ffmpeg lgpl 2.1 or later
#
# some instructions could be saved by using fmac (sv.fmadds, sv.fnmsubs)
# but the accuracy is so high it produces different results.  this
# demo therefore uses fmuls followed by fmsub/fmadd in map-reduce mode
# also note, the FP registers are overwritten, not saved on stack yet.
# at some point 128 registers will be available, meaning that an EABI
# will be defined where there will be plenty of temporaries and no need
# to store 24 FP regs on the stack.

# ints
.set out, 3
.set buf, 4
.set in, 5
.set win, 6

.set i, 7
.set vin, 8
.set vin1, 9
.set vin2, 11
.set pred, %r30

# floats

	.machine libresoc
	.text
	.abiversion 2
	.file	"imdct36_standalone.c"
	.section	.rodata.cst4,"aM",@progbits,4
	.p2align	2               	# -- Begin function imdct36
.LC_zero:
	.long	0                       	# float 0
.LC_2_0:
	.long   0x40000000                     	# float 2
.LC_0_5:
	.long	1056964608              	# float 0.5
.LCPI0_2:
	.long	1064341426              	# float 0.939692616
.LCPI0_3:
	.long	3190935764              	# float -0.173648179
.LCPI0_4:
	.long	3208911741              	# float -0.766044437
.LCPI0_5:
	.long	3210589143              	# float -0.866025388
.LCPI0_6:
	.long	1065098332              	# float 0.984807729
.LCPI0_7:
	.long	3199147332              	# float -0.342020154
.LCPI0_8:
	.long	1063105495              	# float 0.866025388
.LCPI0_9:
	.long	3206843835              	# float -0.642787635
	.text
	.globl	imdct36
	.p2align	4
	.type	imdct36,@function
imdct36:                                	# @imdct36
.Lfunc_begin0:
.Lfunc_gep0:
	addis 2, 12, .TOC.-.Lfunc_gep0@ha
	addi 2, 2, .TOC.-.Lfunc_gep0@l
.Lfunc_lep0:
	.localentry	imdct36, .Lfunc_lep0-.Lfunc_gep0
# %bb.0:
	std 30, -16(1)                  	# 8-byte Folded Spill
	std 3, -24(1)
	std 4, -32(1)
	std 5, -40(1)
	std 6, -48(1)

.loop1:
	setvl 0,0,18,0,1,1			# Set VL to 18 elements
	# Load 18 floats from (in)
	sv.lfs *vin, 0(in)
	# equivalent to: for (i = 17; i >= 1; i--) in[i] += in[i-1];
	sv.fadds/mrr *vin1, *vin1, *vin
	# SETVL to 16 as the next loop is from 1-17 floats to (out)
	setvl 0,0,16,0,1,1
	li 30, 0
        ori 30, 30, 0xaaaa			# Predicate mask 0b1010101010101010
	# equivalent to: for (i = 17; i >= 3; i -= 2) in[i] += in[i-2];
        sv.fadds/mrr/m=pred *vin2, *vin2, *vin1
	# Use SETVL again as we want to store 18 floats to (out)
	setvl 0,0,18,0,1,1
	sv.stfs *vin, 0(out)

	# Load 2.0f constant in register 29, will be needed for SHR macro
	# fmvis 29, 0x4000

	# Use SETVL 2 for the next loop and calculate first the temporary variables, t1,t2,t3
	# equivalent to:
	# for (j = 0; j < 2; j++) {
	#   in1 = in + j;
	#   t1 = in1[2*0] - in1[2*6];
	#   t2 = in1[2*4] + in1[2*8] - in1[2*2];
	#   t3 = in1[2*8] + SHR(in1[2*6],1);
	#   t4 = t1 - SHR(t2, 1);
	#   t5 = t1 + t2;
	# }
	# t1 -> r32-r34
	# t2 -> r35-r37
	# t3 -> r38-r40
	# t4 -> r41-r43
	# t5 -> r44-r46
	# Similarly, the values of 'in' array are already in registers 8-26
	setvl 0,0,2,0,1,1
	# t1
	sv.fsubs *32, *8, *20
	# t2
	sv.fadds *35, *16, *24
	sv.fsubs *35, *35, *12
	# t3, SHR(a,b) = a * 1.0f/(1 << (1)) = a / 2 essentially fdiv a, a, 2.0
	sv.fdivs *38, *20, 29
	sv.fadds *38, *38, *8
	# t4, essentially fdiv *41, *35, 29
	sv.fdivs *41, *35, 29
	sv.fsubs *41, *32, *41
	# t5
	sv.fadds *44, *32, *35

	# Use SETVL again as we want to store 18 floats to (out)
	setvl 0,0,18,0,1,1
	sv.stfs *32, 0(3)
	blr
	.long	0
	.quad	0
.Lfunc_end0:
	.size	imdct36, .Lfunc_end0-.Lfunc_begin0
                                        # -- End function
	.type	icos36h,@object         # @icos36h
	.section	.rodata,"a",@progbits
	.p2align	2
icos36h:
	.long	1048608043              # float 0.250954956
	.long	1048871918              # float 0.258819044
	.long	1049443197              # float 0.275844485
	.long	1050427991              # float 0.305193633
	.long	1052050675              # float 0.353553385
	.long	1054812484              # float 0.435861707
	.long	1050111961              # float 0.295775205
	.long	1056392938              # float 0.482962906
	.long	0                       # float 0
	.size	icos36h, 36

	.type	icos36,@object          # @icos36
	.p2align	2
icos36:
	.long	1056996651              # float 0.501909912
	.long	1057260526              # float 0.517638087
	.long	1057831805              # float 0.551688969
	.long	1058816599              # float 0.610387265
	.long	1060439283              # float 0.707106769
	.long	1063201092              # float 0.871723413
	.long	1066889177              # float 1.18310082
	.long	1073170154              # float 1.93185163
	.long	1085772884              # float 5.73685646
	.size	icos36, 36


	.ident	"clang version 7.0.1-8+deb10u2 (tags/RELEASE_701/final)"
	.section	".note.GNU-stack","",@progbits
#	.addrsig
#	.addrsig_sym imdct36
#	.addrsig_sym icos36h
#	.addrsig_sym icos36

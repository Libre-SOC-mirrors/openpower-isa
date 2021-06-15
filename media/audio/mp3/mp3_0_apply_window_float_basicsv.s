# ffmpeg lgpl 2.1 or later

# ints
.set buf, 3
.set win, 4
.set out, 6
.set incr, 7

.set p, 5
.set i, 8
.set out2, 10

# SV ints, so we don't have to play with the stack
#.set win2, 32
# for now... TODO, add 128 regs to simulator
.set win2, 16

# SV floats
#.set fv0, 32
#.set fv1, 40
#.set fv2, 48
# for now... TODO, add 128 regs to simulator
.set fv0, 8
.set fv1, 16
.set fv2, 24

# floats
.set sum, 0
.set sum2, 1
.set tmpsum, 2
.set tmpsum2, 3

	.machine power9
	.abiversion 2
	.section	".text"
	.align 2
	.p2align 4,,15
	.globl ff_mpadsp_apply_window_float_sv
	.type	ff_mpadsp_apply_window_float_sv, @function
ff_mpadsp_apply_window_float_sv:
.LCF0:
	addis 2,12,.TOC.-.LCF0@ha
	addi 2,2,.TOC.-.LCF0@l

	addis 9,2,.LC0@toc@ha
	addi 9,9,.LC0@toc@l

	slwi incr, incr, 2 # incr *= 4, sizeof float

	mulli 0, incr, 31
	add out2, out, 0

	# set predicate mask (for taking out one add in mapreduce)
	addi 30, 0, 127 # 127 = 0b0111_1111 - 7 bits

	# set Vector Length
	setvl 0, 0, 7, 1, 1 # setvli MVL=8, VL=8
	# sv.addi win2, win, 124

	lfiwax sum, 0, 9 # zero it
	addi p, buf, 64

	# SUM8(MACS, sum, w, p)
	# sv.lfs/els fv0.v, 256(win)
	# sv.lfs/els fv1.v, 256(p)
	# TODO sv.fmadds/mr sum, fv0.v, fv1.v
	# sv.fmuls fv0.v, fv0.v, fv1.v
	# sv.fadds/mr/m=r30 sum, fv0.v, sum

	lfiwax tmpsum, 0, 9 # zero it
	addi p, buf, 192
	addi win, win, 128
	# SUM8(MLSS, sum, w + 32, p)
	# sv.lfs/els fv0.v, 256(win)
	# sv.lfs/els fv1.v, 256(p)
	# TODO sv.fmadds/mr tmpsum, fv0.v, fv1.v
	# sv.fmuls fv0.v, fv0.v, fv1.v
	# sv.fadds/mr/m=r30 tmpsum, fv0.v, tmpsum
	fsubs sum, sum, tmpsum
	subi win, win, 128

	stfs sum, 0(out)
	add out, out, incr
	addi win, win, 4

	# Loop 15 times
	li 0, 15
	mtctr 0
	li i, 4
.Lloop:
		lfiwax sum, 0, 9 # zero it
		lfiwax sum2, 0, 9 # zero it
		addi p, buf, 64
		add p, p, i

		# SUM8P2(sum, MACS, sum2, MLSS, w, w2, p)
		# sv.lfs/els fv0.v, 256(p)
		# sv.lfs/els fv1.v, 256(win)
		# sv.lfs/els fv2.v, 256(win2)
		# TODO sv.fmadds/mr sum, fv0.v, fv1.v
		# sv.fmuls fv1.v, fv0.v, fv1.v
		# sv.fadds/mr/m=r30 sum, fv1.v, sum
		# TODO sv.fmadds/mr sum2, fv0.v, fv2.v
		# sv.fmuls fv0.v, fv0.v, fv2.v
		# sv.fadds/mr/m=r30 sum2, fv0.v, sum2
		fneg sum2, sum2

		addi p, buf, 192
		subf p, i, p
		lfiwax tmpsum, 0, 9 # zero it
		lfiwax tmpsum2, 0, 9 # zero it
		addi win, win, 128
		# sv.addi win2, win2, 128

		# SUM8P2(sum, MLSS, sum2, MLSS, w + 32, w2 + 32, p)
		# sv.lfs/els fv0.v, 256(p)
		# sv.lfs/els fv1.v, 256(win)
		# sv.lfs/els fv2.v, 256(win2)
		# TODO sv.fmadds/mr tmpsum, fv0.v, fv1.v
		# sv.fmuls fv1.v, fv0.v, fv1.v
		# sv.fadds/mr/m=r30 tmpsum, fv1.v, tmpsum
		# TODO sv.fmadds/mr tmpsum2, fv0.v, fv2.v
		# sv.fmuls fv0.v, fv0.v, fv2.v
		# sv.fadds/mr/m=r30 tmpsum2, fv0.v, tmpsum2
		fsubs sum, sum, tmpsum
		fsubs sum2, sum2, tmpsum2

		subi win, win, 128
		# sv.addi win2, win2, -128

		stfs sum, 0(out)
		add out, out, incr
		stfs sum2, 0(out2)
		subf out2, incr, out2

		addi i, i, 4
		addi win, win, 4
		# sv.addi win2, win2, -4
	bdnz .Lloop

	addi p, buf, 128
	addi win, win, 128
	lfiwax sum, 0, 9 # zero it
	# SUM8(MLSS, sum, w + 32, p)
	# sv.lfs/els fv0.v, 256(win)
	# sv.lfs/els fv1.v, 256(p)
	# TODO sv.fmadds/mr sum, fv0.v, fv1.v
	# sv.fmuls fv0.v, fv0.v, fv1.v
	# sv.fadds/mr/m=r30 sum, fv0.v, sum
	# XXX no? possible bug? fneg sum, sum

	stfs sum, 0(out)

	blr

	.size	ff_mpadsp_apply_window_float_sv,.-ff_mpadsp_apply_window_float_sv

	.section        .rodata
	.align 2
	.LC0:
	.long   0

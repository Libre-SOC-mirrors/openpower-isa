# ffmpeg lgpl 2.1 or later

# ints
.set buf, 3
.set win, 4
.set out, 6
.set incr, 7

.set p, 5
.set i, 8
.set out2, 10

# floats
.set sum, 0
.set sum2, 1

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

	# w2 = window + 31; TODO
	lfiwax sum, 0, 9 # zero it
	addi p, buf, 64
	# SUM8(MACS, sum, w, p); TODO
	addi p, buf, 192
	# SUM8(MLSS, sum, w + 32, p); TODO
	stfs sum, 0(out)
	add out, out, incr
	addi win, win, 4

	# Loop 15 times
	li 0, 15
	mtctr 0
	li i, 4
.Lloop:
		lfiwax sum, 0, 9 # zero it
		addi p, buf, 64
		add p, p, i
		# SUM8P2(sum, MACS, sum2, MLSS, w, w2, p);TODO
		addi p, buf, 192
		subf p, i, p
		# SUM8P2(sum, MLSS, sum2, MLSS, w + 32, w2 + 32, p); TODO

		stfs sum, 0(out)
		add out, out, incr
		stfs sum2, 0(out2)
		subf out2, incr, out2

		addi i, i, 4
		addi win, win, 4
		subi win2, win2, 4
	bdnz .Lloop

	addi p, buf, 128
	# SUM8(MLSS, sum, w + 32, p); TODO
	stfs sum, 0(out)

	blr

	.size	ff_mpadsp_apply_window_float_sv,.-ff_mpadsp_apply_window_float_sv

	.section        .rodata
	.align 2
	.LC0:
	.long   0

# ffmpeg lgpl 2.1 or later

# ints
.set buf, 3
.set win, 4
.set out, 6
.set incr, 7

.set p, 5
.set i, 8

# floats
.set sum, 0

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

	# Loop 32 times
	li 0, 32
	mtctr 0
	li i, 0
.Lloop:
		lfiwax sum, 0, 9 # zero it
		addi p, buf, 64
		add p, p, i
		# SUM8(MACS, sum, w, p) TODO
		addi p, buf, 192
		subf p, i, p
		# SUM8(MLSS, sum, w + 32, p) TODO
		stfs sum, 0(out)
		add out, out, incr
		addi i, i, 4
		addi win, win, 4
	bdnz .Lloop

	blr

	.size	ff_mpadsp_apply_window_float_sv,.-ff_mpadsp_apply_window_float_sv

	.section        .rodata
	.align 2
	.LC0:
	.long   0

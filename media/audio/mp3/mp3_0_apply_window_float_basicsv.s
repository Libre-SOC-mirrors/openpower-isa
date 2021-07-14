# ffmpeg lgpl 2.1 or later
#
# some instructions could be saved by using fmac (sv.fmadds, sv.fnmsubs)
# but the accuracy is so high it produces different results.  this
# demo therefore uses fmuls followed by fmsub/fmadd in map-reduce mode
# also note, the FP registers are overwritten, not saved on stack yet.
# at some point 128 registers will be available, meaning that an EABI
# will be defined where there will be plenty of temporaries and no need
# to store 24 FP regs on the stack.

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
.set fv0, 32
.set fv1, 40
.set fv2, 48

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

	# samples2 = samples + 31 * incr;
	slwi incr, incr, 2 # incr *= 4, sizeof float
	mulli 0, incr, 31
	add out2, out, 0

	# set Vector Length
	setvl 0, 0, 8, 1, 1, 0# setvli MVL=8, VL=8
	addi win2, win, 124   # w2 = window + 31

	lfiwax sum, 0, 5      # sum = *dither_state
	addi p, buf, 64       # p = synth_buf+16

	# SUM8(MACS, sum, w, p)
	# sv.lfs/els fv0.v, 256(win)
	# sv.lfs/els fv1.v, 256(p)
	# TOO ACCURATE! hilarious sv.fmadds/mr sum, fv0.v, fv1.v, sum
	# sv.fmuls fv0.v, fv0.v, fv1.v
	# sv.fadds/mr sum, fv0.v, sum

	addi p, buf, 192      # p = synth_buf + 48;
	addi win, win, 128    # w = w + 32
	# SUM8(MLSS, sum, w + 32, p)
	# sv.lfs/els fv0.v, 256(win)
	# sv.lfs/els fv1.v, 256(p)
	# TOO ACCURATE! hilarious sv.fnmsubs/mr sum, fv0.v, fv1.v, sum
	# sv.fmuls fv0.v, fv0.v, fv1.v
	# sv.fsubs/mr sum, sum, fv0.v
	addi win, win, -128   # w = w - 32

	stfs sum, 0(out)      # *samples = &sum
	add out, out, incr    # samples += incr
	addi win, win, 4      # w++

	# Loop 15 times
	li 0, 15
	mtctr 0
	li i, 4  # loop starts at 1: (for j=1;j<16;j++)
.Lloop:
		lfiwax sum, 0, 9 # zero it
		lfiwax sum2, 0, 9 # zero it

		# p = synth_buf + 16 + j
		addi p, buf, 64
		add p, p, i

		# SUM8P2(sum, MACS, sum2, MLSS, w, w2, p)
		# sv.lfs/els fv0.v, 256(p)
		# sv.lfs/els fv1.v, 256(win)
		# sv.lfs/els fv2.v, 256(win2)
		# TOO ACCURATE! hilarious sv.fmadds/mr sum, fv0.v, fv1.v, sum
		# TOO ACCURATE! hilarious sv.fnmsubs/mr sum2, fv0.v, fv2.v, sum2
		# sv.fmuls fv1.v, fv0.v, fv1.v
		# sv.fadds/mr sum, sum, fv1.v
		# sv.fmuls fv0.v, fv0.v, fv2.v
		# sv.fsubs/mr sum2, sum2, fv0.v

		# p = synth_buf + 48 - j
		addi p, buf, 192
		subf p, i, p

		# win and win2 += 32
		addi win, win, 128
		addi win2, win2, 128

		# SUM8P2(sum, MLSS, sum2, MLSS, w + 32, w2 + 32, p)
		# sv.lfs/els fv0.v, 256(p)
		# sv.lfs/els fv1.v, 256(win)
		# sv.lfs/els fv2.v, 256(win2)
		# TOO ACCURATE! hilarious sv.fnmsubs/mr sum, fv0.v, fv1.v, sum
		# TOO ACCURATE! hilarious sv.fnmsubs/mr sum2, fv0.v, fv2.v, sum2
		# sv.fmuls fv1.v, fv0.v, fv1.v
		# sv.fsubs/mr sum, sum, fv1.v
		# sv.fmuls fv0.v, fv0.v, fv2.v
		# sv.fsubs/mr sum2, sum2, fv0.v

		# win and win2 -= 32
		addi win, win, -128
		addi win2, win2, -128

		stfs sum, 0(out)
		add out, out, incr    # samples += incr
		stfs sum2, 0(out2)
		subf out2, incr, out2 # samples2 -= incr

		addi i, i, 4          # for-loop j=1..15
		addi win, win, 4      # w++
		addi win2, win2, -4   # w2--
	bdnz .Lloop

	addi p, buf, 128        # p = synth_buf + 32
	addi win, win, 128      # w += 32
	lfiwax sum, 0, 9 # zero it
	# SUM8(MLSS, sum, w + 32, p)
	# sv.lfs/els fv0.v, 256(win)
	# sv.lfs/els fv1.v, 256(p)
	# TOO ACCURATE! hilarious sv.fnmsubs/mr sum, fv0.v, fv1.v, sum
	# sv.fmuls fv0.v, fv0.v, fv1.v
	# sv.fsubs/mr sum, sum, fv0.v

	stfs sum, 0(out)

	blr

	.size	ff_mpadsp_apply_window_float_sv,.-ff_mpadsp_apply_window_float_sv

	.section        .rodata
	.align 2
	.LC0:
	.long   0

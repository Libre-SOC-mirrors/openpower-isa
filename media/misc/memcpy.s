	.file	"memcpy.c"
	.machine power9
	.abiversion 2
	.section	".text"
	.align 2
	.globl memcpy
	.type	memcpy, @function
memcpy:
	std 31,-8(1)
	stdu 1,-96(1)
	mr 31,1
	std 3,48(31)
	std 4,56(31)
	std 5,64(31)
	ld 9,48(31)
	std 9,32(31)
	ld 9,56(31)
	std 9,40(31)
	b .Lmemcpy_2
.Lmemcpy_3:
	ld 10,40(31)
	addi 9,10,1
	std 9,40(31)
	ld 9,32(31)
	addi 8,9,1
	std 8,32(31)
	lbz 10,0(10)
	stb 10,0(9)
.Lmemcpy_2:
	ld 9,64(31)
	addi 10,9,-1
	std 10,64(31)
	cmpdi 0,9,0
	bne 0,.Lmemcpy_3
	ld 9,48(31)
	mr 3,9
	addi 1,31,96
	ld 31,-8(1)
	blr
	.long 0
	.byte 0,0,0,0,128,1,0,1
	.size	memcpy,.-memcpy
	.ident	"GCC: (GNU) 10.3.0"
	.section	.note.GNU-stack,"",@progbits

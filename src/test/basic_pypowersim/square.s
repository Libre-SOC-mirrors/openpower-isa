        std 31,-8(1)
        stdu 1,-48(1)
        mr 31,1
        li 12,5
.L3:
        mr 9,12
        addi 9,9,-1
        mr 12,9
        mr 9,12
        cmpdi 7,9,0
        beq 7,.L4
        b .L3
.L4:
        addi 1,31,48
        ld 31,-8(1)
        attn
        .long 0
        .byte 0,9,0,0,128,1,0,1

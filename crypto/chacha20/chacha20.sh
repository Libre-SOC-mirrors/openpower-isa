#!/bin/sh -xe


pypowersim -g chacha20.gpr \
	-s common.spr \
	-p 0x20000000 \
    -l ./chacha20.key:0x600000 \
    -l ./chacha20.iv:0x700000 \
    -l ./chacha20.cipher:0x800000 \
    -l ./chacha20.plain:0x900000 \
    -d ./chacha20.out:0x500000:128 \
	-i chacha20test.bin
#cmp ${2} data/audio/mp3/mp3_0_data/samples${1}

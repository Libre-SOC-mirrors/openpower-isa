#!/bin/sh -xe

#-l data/audio/mp3/mp3_0_data/buf${1}:0x600000 \
#-l data/audio/mp3/mp3_0_data/win0:0x700000 \

pypowersim -g chacha20.gpr \
	-s common.spr \
	-p 0x20000000 \
	-d ${2}:0x900000:128 \
	-i chacha20test.bin
#cmp ${2} data/audio/mp3/mp3_0_data/samples${1}

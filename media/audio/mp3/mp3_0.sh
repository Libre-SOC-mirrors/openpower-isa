#!/bin/sh -xe

pypowersim -g audio/mp3/mp3_0.gpr \
	-s common.spr \
    -p 0x20000000 \
	-l data/audio/mp3/mp3_0_data/buf${1}:0x20100000 \
	-l data/audio/mp3/mp3_0_data/win0:0x20200000 \
	-d ${2}:0x20400000:128 \
	-i audio/mp3/mp3_0_apply_window_float.bin
cmp ${2} data/audio/mp3/mp3_0_data/samples${1}

#!/bin/sh -xe

pypowersim -g audio/mp3/mp3_1.gpr \
	-s common.spr \
	-l data/audio/mp3/mp3_1_data/beforeout${1}:0x100000 \
	-l data/audio/mp3/mp3_1_data/buf${1}:0x200000 \
	-l data/audio/mp3/mp3_1_data/in${1}:0x300000 \
	-l data/audio/mp3/mp3_1_data/win${1}:0x400000 \
	-d ${DUMP}:0x100000:2304 \
	-i audio/mp3/mp3_1_imdct36_float.bin
cmp ${DUMP} data/audio/mp3/mp3_1_data/out${1}

.PHONY: all wget tests

CROSS ?= powerpc64-linux-gnu-
AS = $(CROSS)as
LD = $(CROSS)ld
OBJCOPY = $(CROSS)objcopy

AFLAGS ?= -mpwr9

EXPECTED_VER = 1
VER = $(shell cat data/VERSION)

SRC = $(wildcard audio/*/*.s video/*/*.s)
OBJ = $(SRC:.s=.bin)

DUMP = /tmp/out

# commented for luke's convenience
#export SILENCELOG = 1

all:
ifneq ($(VER), $(EXPECTED_VER))
	$(error Data not found, or version mismatch. Please run "make wget")
endif
	@$(MAKE) tests

wget:
	mkdir -p data
	rm -f media-test-data.txz
	wget https://ftp.libre-soc.org/media-test-data.txz
	tar -C data -xvf media-test-data.txz

%.bin: %.s
	pysvp64asm $< $<.sv
	$(AS) $(AFLAGS) -c $<.sv -le -o $<.o
	$(LD) $<.o -EL -o $<.elf -T memmap
	$(OBJCOPY) $<.elf -I elf64-little -O binary $@

tests: $(OBJ)
	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf0:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples0

	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf1000:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples1000

	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf2000:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples2000

	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf3000:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples3000

	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf4000:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples4000

	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf5000:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples5000

	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf6000:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples6000

	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf7000:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples7000

	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf8000:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples8000

	pypowersim -g audio/mp3/mp3_0.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_0_data/buf9000:0x100000 \
		-l data/audio/mp3/mp3_0_data/win0:0x200000 \
		-d $(DUMP):0x400000:128 \
		-i audio/mp3/mp3_0_apply_window_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_0_data/samples9000

	##

	pypowersim -g audio/mp3/mp3_1.gpr \
		-s common.spr \
		-l data/audio/mp3/mp3_1_data/beforeout0:0x100000 \
		-l data/audio/mp3/mp3_1_data/buf0:0x200000 \
		-l data/audio/mp3/mp3_1_data/in0:0x300000 \
		-l data/audio/mp3/mp3_1_data/win0:0x400000 \
		-d $(DUMP):0x100000:2304 \
		-i audio/mp3/mp3_1_imdct36_float.bin
	cmp $(DUMP) data/audio/mp3/mp3_1_data/out0

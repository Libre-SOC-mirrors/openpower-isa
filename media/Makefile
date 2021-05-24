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
	echo juuh
	pypowersim -g audio/mp3/mp3_0.gpr \
                -i audio/mp3/mp3_0_apply_window_float.bin

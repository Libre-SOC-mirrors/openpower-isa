.PHONY: all wget tests

CROSS ?= powerpc64le-linux-gnu-
AS = $(CROSS)as
LD = $(CROSS)ld
OBJCOPY = $(CROSS)objcopy

PYSVP64TRANS ?= cp
AFLAGS ?= -mlibresoc

EXPECTED_VER = 1
VER = $(shell cat data/VERSION)

SRC = $(wildcard audio/*/*.s video/*/*.s)
OBJ = $(SRC:.s=.bin)

export DUMP = /tmp/out

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
	$(PYSVP64TRANS) $< $<.sv
	$(AS) $(AFLAGS) -c $<.sv -le -o $<.o
	$(LD) $<.o -EL -o $<.elf -T memmap
	$(OBJCOPY) $<.elf -I elf64-little -O binary $@

tests: $(OBJ)
	@echo audio/mp3_0
	for i in `seq 0 1000 9000`; do \
		audio/mp3/mp3_0.sh $$i $$DUMP$$i || exit 1; \
	done
	@echo audio/mp3_1
	for i in `seq 0 23`; do \
		audio/mp3/mp3_1.sh $$i $$DUMP$$i || exit 1; \
	done


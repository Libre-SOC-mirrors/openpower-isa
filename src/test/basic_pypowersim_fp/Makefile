TOOLCHAIN=powerpc64le-linux-gnu
CC=$(TOOLCHAIN)-gcc
AS=$(TOOLCHAIN)-as
AFLAGS=-mpwr9

all: sim

sim: kernel.bin
	./writefp.sh
	pypowersim -q --load testin.bin:0 \
	           -p 0x20000000 \
               --dump testout.bin:0x20000100:32 \
               --dump testout2.bin:0x0:32 \
               -g gpr.list -f fpr.list -i kernel.bin

clean:
	rm *.o *.elf *.bin

kernel.elf: testfp.o
	$(TOOLCHAIN)-ld $^ -EL -o $@ -T memmap

kernel.bin: kernel.elf
	$(TOOLCHAIN)-objcopy $< -I elf64-little -O binary $@

%.o: %.s
	$(AS) $(AFLAGS) -c $< -le -o $@

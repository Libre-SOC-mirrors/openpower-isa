TOOLCHAIN=powerpc64le-linux-gnu
CC=$(TOOLCHAIN)-gcc
AS=$(TOOLCHAIN)-as
AFLAGS=-mpwr9

all: sim

sim: kernel.bin
	echo -n -e \\0060\\0000\\0061\\0000 > test.bin
	echo -n -e \\0060\\0000\\0061\\0000 >> test.bin
	pypowersim -q --load test.bin:0 \
	           -p 0x20000000 \
               --dump testout.bin:0x20000100:8 \
               --dump testout2.bin:0x0:16 \
               -g gpr.list -i kernel.bin

clean:
	rm *.o *.elf *.bin

kernel.elf: test.o
	$(TOOLCHAIN)-ld $^ -EL -o $@ -T memmap

kernel.bin: kernel.elf
	$(TOOLCHAIN)-objcopy $< -I elf64-little -O binary $@

%.o: %.s
	$(AS) $(AFLAGS) -c $< -le -o $@

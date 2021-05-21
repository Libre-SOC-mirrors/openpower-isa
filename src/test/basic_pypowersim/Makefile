TOOLCHAIN=powerpc64-linux-gnu
CC=$(TOOLCHAIN)-gcc
AS=$(TOOLCHAIN)-as
AFLAGS=-mpwr9

all: sim

sim: kernel.bin
	pypowersim -g gpr.list -i kernel.bin

clean:
	rm *.o *.elf *.bin

kernel.elf: square.o
	$(TOOLCHAIN)-ld $^ -EL -o $@ -T memmap

kernel.bin: kernel.elf
	$(TOOLCHAIN)-objcopy $< -I elf64-little -O binary $@

%.o: %.s
	$(AS) $(AFLAGS) -c $< -le -o $@

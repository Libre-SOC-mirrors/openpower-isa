# A simple Makefile, to build run: make all
TARGET	= test-chacha20

AS = powerpc64le-linux-gnu-as
CC = gcc
LD = ld
CROSSOBJCOPY = powerpc64le-linux-gnu-objcopy
CROSSLD = powerpc64le-linux-gnu-ld

#compiler flags here
CFLAGS = -g3 -O -Wall -Wextra -I../../media/pypowersim_wrapper -I/usr/include/python3.7m

# assembler flags here
ASFLAGS= -mlibresoc -mregnames -Isrc

#linker flags here
LDFLAGS = -Wall -pthread -lpython3.7m

SRCDIR	= src
BINDIR  = bin

CFILES	:= $(SRCDIR)/xchacha20.c $(SRCDIR)/test.c $(SRCDIR)/xchacha20_wrapper.c
ASFILES := $(SRCDIR)/xchacha_hchacha20_svp64.s $(SRCDIR)/xchacha_encrypt_bytes_svp64.s
INCLUDES := $(wildcard $(SRCDIR)/*.h))
SVP64OBJECTS := $(ASFILES:$(SRCDIR)/%.s=$(SRCDIR)/%.o)
OBJECTS := $(CFILES:$(SRCDIR)/%.c=$(SRCDIR)/%.o)
BINFILES := $(BINDIR)/xchacha_hchacha20_svp64.bin $(BINDIR)/xchacha_encrypt_bytes_svp64.bin

$(BINDIR)/%.elf: $(SRCDIR)/%.o
	$(CROSSLD) -EL -o $@ -T memmap $^

$(BINDIR)/%.bin: $(BINDIR)/%.elf
	$(CROSSOBJCOPY) -I elf64-little -O binary $< $@

.PHONY: all clean remove
all: ${TARGET}

$(TARGET): $(OBJECTS) $(SVP64OBJECTS) $(BINFILES)
	$(CC) -o $@ $(OBJECTS) $(LDFLAGS)

clean:
	$ rm -f $(OBJECTS) $(SVP64OBJECTS) $(BINFILES)

remove: clean
	$ rm -f $(TARGET)

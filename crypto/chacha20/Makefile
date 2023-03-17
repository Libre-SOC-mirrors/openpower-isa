# A simple Makefile, to build run: make all
TARGET	= test-chacha20

CROSS ?= powerpc64le-linux-gnu-
AS = $(CROSS)as
CC = $(CROSS)gcc
LD = $(CROSS)ld

#compiler flags here
CFLAGS = -g3 -O -Wall -Wextra -mno-vsx -mno-altivec -I../../media/pypowersim_wrapper -I/usr/include/python3.7m

# assembler flags here
ASFLAGS= -mlibresoc -mregnames -Isrc

#linker flags here
LDFLAGS = -Wall -pthread -lpython3.7m

SRCDIR	= src

CFILES	:= $(SRCDIR)/xchacha20.c $(SRCDIR)/test.c $(SRCDIR)/xchacha20_wrapper.c
ASFILES := $(SRCDIR)/xchacha_hchacha20_svp64.s $(SRCDIR)/xchacha_encrypt_bytes_svp64.s
INCLUDES := $(wildcard $(SRCDIR)/*.h))
OBJECTS	:= $(CFILES:$(SRCDIR)/%.c=$(SRCDIR)/%.o) $(ASFILES:$(SRCDIR)/%.s=$(SRCDIR)/%.o)

.PHONY: all clean remove
all: ${TARGET}

$(TARGET): $(OBJECTS)
	$(CC) -o $@ $(OBJECTS) $(LDFLAGS)

clean:
	$ rm -f $(OBJECTS)

remove: clean
	$ rm -f $(TARGET)

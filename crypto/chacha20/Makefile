# A simple Makefile, to build run: make all
TARGET	= test

CROSS ?= powerpc64le-linux-gnu-
AS = $(CROSS)as
CC = $(CROSS)gcc
LD = $(CROSS)ld

#compiler flags here
CFLAGS = -O3 -Wall -Wextra -static -mno-vsx -mno-altivec

#linker flags here
LDFLAGS = -Wall -static

SRCDIR	= src

SOURCES	:= $(SRCDIR)/xchacha20.c $(SRCDIR)/test.c
INCLUDES	:= $(wildcard $(SRCDIR)/*.h))
OBJECTS	:= $(SOURCES:$(SRCDIR)/%.c=$(SRCDIR)/%.o)

.PHONY: all clean remove
all: ${TARGET}

$(TARGET): $(OBJECTS)
	$(CC) -o $@ $(LDFLAGS) $(OBJECTS)

$(OBJECTS): $(SRCDIR)/%.o : $(SRCDIR)/%.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	$ rm -f $(OBJECTS)

remove: clean
	$ rm -f $(TARGET)

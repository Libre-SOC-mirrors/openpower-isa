TARGET=dav1d_svp64_test

CC=gcc
CXX=g++
AS=powerpc64le-linux-gnu-as
OBJCOPY=powerpc64le-linux-gnu-objcopy
CFLAGS= -O -g3 -std=c99 -I../../pypowersim_wrapper -I. -Iinclude -I/usr/include/python3.7m -DHAVE_SVP64 -D_GNU_SOURCE -DNDEBUG -D_FILE_OFFSET_BITS=64 -DBITDEPTH=16 -Wundef -Werror=vla -Wno-maybe-uninitialized -Wno-missing-field-initializers -Wno-unused-parameter -Wstrict-prototypes -Werror=missing-prototypes -fomit-frame-pointer
CXXFLAGS= -Iinclude -O -g3
ASFLAGS= -mlibresoc -mregnames
LDFLAGS=-lgtest -pthread -lpython3.7m

BINFILES = 
ASFILES  = src/ppc/cdef_tmpl_svp64_real.s
CFILES   = cdef.c checkasm.c src/cpu.c src/ppc/cpu.c src/ppc/cdef_tmpl_svp64_wrapper.c src/cdef_tmpl.c src/tables.c src/log.c
CPPFILES = 
OBJFILES = $(ASFILES:.s=.o) $(CFILES:.c=.o) $(CPPFILES:.cc=.o)

%.bin: %.o
	${OBJCOPY} -I elf64-little -O binary $< $@ 

${TARGET}: ${OBJFILES}
	#${OBJCOPY} --globalize-symbols=src/filmgrain_tmpl.symbols src/filmgrain_tmpl.o
	${CXX} -o ${TARGET} ${OBJFILES} ${LDFLAGS}

all: ${TARGET} ${BINFILES}

.PHONY: clean
clean:
	rm -f ${TARGET} ${OBJFILES} ${BINFILES}

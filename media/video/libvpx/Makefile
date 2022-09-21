TARGET=libvpx_variance_test
EXAMPLE=pypowersim_wrapper_example

CC=gcc
CXX=g++
AS=powerpc64le-linux-gnu-as
OBJCOPY=powerpc64le-linux-gnu-objcopy
CFLAGS= -Iinclude -O -g3 -I/usr/include/python3.7m
CXXFLAGS= -Iinclude -O -g3
ASFLAGS= -mlibresoc
LDFLAGS=-lgtest -pthread -lpython3.7m

BINFILES = vpx_get_mb_ss_svp64_real.bin vpx_get4x4sse_cs_svp64_real.bin 
ASFILES  = vpx_get_mb_ss_svp64_real.s vpx_get4x4sse_cs_svp64_real.s
CFILES   = variance_ref.c  variance_svp64.c  variance_svp64_wrappers.c  vpx_mem.c
CPPFILES = test_libvpx.cc  variance_test.cc
EXAMPLEC = pypowersim_wrapper_example.c
EXAMPLEOBJ= ${EXAMPLEC:.c=.o}
OBJFILES = $(CFILES:.c=.o) $(CPPFILES:.cc=.o) $(ASFILES:.s=.o)

%.bin: %.o
	${OBJCOPY} -I elf64-little -O binary $< $@ 

${TARGET}: ${OBJFILES} ${BINFILES}
	${CXX} -o ${TARGET} ${OBJFILES} ${LDFLAGS}

${EXAMPLE}: ${EXAMPLEOBJ}

all: ${TARGET} ${EXAMPLE}

.PHONY: clean
clean:
	rm -f ${TARGET} ${OBJFILES} ${BINFILES}

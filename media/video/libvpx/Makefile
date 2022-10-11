VPXTARGET=libvpx_variance_test
VP8TARGET=vp8_dct_test

CC=gcc
CXX=g++
AS=powerpc64le-linux-gnu-as
OBJCOPY=powerpc64le-linux-gnu-objcopy
CFLAGS= -Iinclude -I../../pypowersim_wrapper -O -g3 -I/usr/include/python3.7m
CXXFLAGS= -Iinclude -O -g3
ASFLAGS= -mlibresoc -mregnames
LDFLAGS=-lgtest -pthread -lpython3.7m

BINFILES     = vpx_get_mb_ss_svp64_real.bin vpx_get4x4sse_cs_svp64_real.bin variance_svp64_real.bin vp8_dct4x4_real.bin
VP8_ASFILES  = vp8_dct4x4_real.s
VPX_ASFILES  = vpx_get_mb_ss_svp64_real.s vpx_get4x4sse_cs_svp64_real.s variance_svp64_real.s
VP8_CFILES   = vp8_dct4x4_ref.c vp8_dct4x4_wrappers.c
VPX_CFILES   = variance_ref.c  variancefuncs_svp64.c  variance_svp64_wrappers.c  vpx_mem.c
VP8_CPPFILES = test_libvpx.cc  vp8_fdct4x4_test.cc
VPX_CPPFILES = test_libvpx.cc  variance_test.cc
VP8_OBJFILES = $(VP8_ASFILES:.s=.o) $(VP8_CFILES:.c=.o) $(VP8_CPPFILES:.cc=.o)
VPX_OBJFILES = $(VPX_ASFILES:.s=.o) $(VPX_CFILES:.c=.o) $(VPX_CPPFILES:.cc=.o)

%.bin: %.o
	${OBJCOPY} -I elf64-little -O binary $< $@ 

${VP8TARGET}: ${VP8_OBJFILES}
	${CXX} -o ${VP8TARGET} ${VP8_OBJFILES} ${LDFLAGS}

${VPXTARGET}: ${VPX_OBJFILES}
	${CXX} -o ${VPXTARGET} ${VPX_OBJFILES} ${LDFLAGS}

all: ${VP8TARGET} ${VPXTARGET} ${BINFILES}

.PHONY: clean
clean:
	rm -f ${VP8TARGET} ${VPXTARGET} ${VP8_OBJFILES} ${VPX_OBJFILES} ${BINFILES}

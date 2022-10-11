EXAMPLE=pypowersim_wrapper_example

CC=gcc
CXX=g++
AS=powerpc64le-linux-gnu-as
OBJCOPY=powerpc64le-linux-gnu-objcopy
CFLAGS= -Iinclude -O -g3 -I/usr/include/python3.7m
CXXFLAGS= -Iinclude -O -g3
ASFLAGS= -mlibresoc -mregnames
LDFLAGS=-lgtest -pthread -lpython3.7m

EXAMPLEC     = pypowersim_wrapper_example.c
EXAMPLEOBJ   = ${EXAMPLEC:.c=.o}

${EXAMPLE}: ${EXAMPLEOBJ}

all: ${EXAMPLE}

.PHONY: clean
clean:
	rm -f ${EXAMPLE} ${EXAMPLEOBJ}

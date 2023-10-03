CC=gcc
CFLAGS=-O2 -DPOLY1305_64BIT
SRCS=poly1305-rand-test.c poly1305-donna.c
OBJS=$(SRCS:.c=.o)

BIN=poly1305-rand-test

.PHONY: depend clean

all: $(BIN)

$(BIN): $(OBJS)
	$(CC) $(CFLAGS) $(INCLUDES) -o $(BIN) $(OBJS) $(LFLAGS) $(LIBS)

.c.o:
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@


clean:
	rm -rf $(MAIN) $(OBJS) $(BIN)
install:
	cp ./$(BIN) /usr/bin/$(BIN)

depend: $(SRCS)
	makedepend $(INCLUDES) $^

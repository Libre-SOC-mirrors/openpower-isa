fft-real: fft-real-pair.c fft-real-pair-test.c fft-real-pair.h
	powerpc64le-linux-gnu-gcc -S -fverbose-asm -mno-vsx \
                                 fft-real-pair.c -o fft-real-pair.s
	gcc fft-real-pair.c fft-real-pair-test.c fft-real-pair.h -o fft-real -lm

clean:
	rm fft-real

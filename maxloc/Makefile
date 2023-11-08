.PHONY: all clean

all: maxloc

maxloc: maxloc.c
	gcc maxloc.c -o maxloc
	#gcc -Os -mno-vsx -mno-altivec maxloc.c -o maxloc

clean:
	rm -rf maxloc

#!/bin/bash
set -xe
clang --target=powerpc64le-linux-gnu -Og -g -c -o jit_test.o jit_test.cpp
powerpc64le-linux-gnu-objcopy --set-section-flags .wtext=CONTENTS,ALLOC,LOAD,CODE jit_test.o
powerpc64le-linux-gnu-gcc -static -o jit_test jit_test.o
set +e
for i in {-3..3}; do
    printf -v ih "%#x" "$i"
    for j in {-3..3}; do
        printf -v jh "%#x" "$j"
        ./jit_test "$ih" "$jh"
        echo "return value $? -- should be $(((i + j) & 0xFF))"
    done
done

#!/bin/sh
qemu-system-ppc64le -machine powernv9 \
                  -cpu power9 \
                  -nographic \
                  -s -S -m size=4096 \
                  -kernel kernel.bin > /dev/null &

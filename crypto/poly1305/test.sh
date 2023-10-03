#!/bin/bash
make
while true
do
    ./poly1305-rand-test > rand.csv
    python3 poly1305-donna-test.py
done

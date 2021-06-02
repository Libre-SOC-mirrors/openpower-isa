#!/bin/bash
echo -n -e '\x66\x66\x02\x42' > testin.bin
echo -n -e '\x00\x00\x80\x3f' >> testin.bin
echo -n -e '\x00\xa0\x7e\x31' >> testin.bin
echo -n -e '\x00\x00\x7e\x31' >> testin.bin
echo -n -e '\x00\x00\x00\x00' >> testin.bin
echo -n -e '\x00\x00\x00\x00' >> testin.bin
echo -n -e '\x00\x00\x00\x00' >> testin.bin
echo -n -e '\x00\x00\x00\x00' >> testin.bin
echo -n -e '\x00\x00\x00\x00' >> testin.bin
echo -n -e '\x00\x00\x00\x00' >> testin.bin
echo -n -e '\x00\x00\x00\x00' >> testin.bin
echo -n -e '\x00\x00\x00\x00' >> testin.bin


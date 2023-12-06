# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2023 Jacob Lifshay <programmerjake@gmail.com>
# Funded by NLnet http://nlnet.nl
""" ELF test utilities

related bugs:

* https://bugs.libre-soc.org/show_bug.cgi?id=1169
"""

from subprocess import run, PIPE
from tempfile import NamedTemporaryFile
from elftools.elf.elffile import ELFFile
from openpower.util import log, LogType

DEF_CC_ARGS = '-Os', '-ffreestanding', '-nostdlib', '-static', '-xc'
DEF_CC = 'powerpc64le-linux-gnu-gcc'

def compile_elf(src_code, compiler_args=DEF_CC_ARGS, compiler=DEF_CC):
    if isinstance(compiler, str):
        compiler = [compiler]
    f = NamedTemporaryFile(suffix=".elf")
    args = [*compiler, *compiler_args, '-', '-o', f.name]
    cleanup = f.close
    try:
        run(args, input=src_code, check=True, encoding='utf-8')
        dump_out = run([
            'powerpc64le-linux-gnu-objdump', '-dfprsF', '-Mraw', f.name],
            stdout=PIPE, check=True, encoding='utf-8').stdout
        log(dump_out)
        f = ELFFile(f)
        cleanup = None
        return f
    finally:
        if cleanup is not None:
            cleanup()
